import argparse
import asyncio
import logging
import os
from pathlib import Path

import PIL.Image
import yaml
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

from restabot.model import OcrTaskInput, OcrTaskOutput, Restaurant

LOG = logging.getLogger(f'{__package__}.ocr')


OCR_PROMPT = (
    'Extract daily menus from the image. The text is in Czech language. '
    'If the menus cannot be extracted, please respond with an error message '
    'and leave `daily_menus` field empty.'
)


class Meal(BaseModel):
    name: str = Field(description='Name of the meal in Czech language')
    description: str | None = Field(description='Additional information about the meal.')
    is_vegetarian: bool
    price: str


class DailyMenu(BaseModel):
    day: str = Field(description='Date or day of the week, depending on what can be extracted.')
    meals: list[Meal]


class ParsedMenu(BaseModel):
    message: str = Field(description='Message summarizing if the extraction was successful.')
    daily_menus: list[DailyMenu] = Field(
        description='List of menus for each day. It is possible that there is only one day mentioned.')


async def ocr_task(input: OcrTaskInput) -> OcrTaskOutput:
    with input.site_config_file.open('rt', encoding='utf-8') as f:
        site_data = yaml.safe_load(f)

    sites = [Restaurant.model_validate(rest_dict) for rest_dict in site_data['restaurants']]

    out_dir = input.out_dir
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
    elif not out_dir.is_dir():
        raise ValueError(f'{out_dir} is not a directory')
    out_dir = out_dir.resolve()

    image = PIL.Image.open(input.in_dir / f'{sites[0].id}.jpeg')

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[image, OCR_PROMPT],
        config={
            'response_mime_type': 'application/json',
            'response_schema': ParsedMenu,
        },
    )
    print(response.parsed.model_dump_json(indent=2))

    return OcrTaskOutput(results=[], errors=[])


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Parse screenshots of webpages')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--in-dir', required=True, help='Path to input directory')
    parser.add_argument('--out-dir', required=True, help='Path to output directory')
    args = parser.parse_args()

    load_dotenv()

    await ocr_task(OcrTaskInput(
        site_config_file=Path(args.sites),
        in_dir=Path(args.in_dir),
        out_dir=Path(args.out_dir)
    ))


if __name__ == "__main__":
    asyncio.run(main())
