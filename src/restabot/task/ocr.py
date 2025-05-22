import argparse
import asyncio
import datetime
import logging
import os
from pathlib import Path

import PIL.Image
import yaml
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig

from restabot.model import ErrorResult, OcrResult, OcrTaskInput, OcrTaskOutput, ParsedMenu, Restaurant

LOG = logging.getLogger(f'{__package__}.ocr')

MODEL = 'gemini-2.5-flash-preview-05-20'
# MODEL = 'gemini-2.0-flash'

OCR_PROMPT_TMPL = (
    'Extract restaurant daily menus from the image. The texts are in Czech or English language. '
    'The input is either a screenshot of a webpage or a photo of a handwritten menu; it can contain spelling errors. '
    'Ignore any text not related to the menu.'
)


def get_ocr_prompt(date: datetime.date) -> str:
    return OCR_PROMPT_TMPL.format(date=date.isoformat())


async def ocr_task(input: OcrTaskInput) -> OcrTaskOutput:
    """
    Run OCR on all the images in `input.in_dir` and return the extracted menus.

    The function uses the Gemini API to perform the OCR. The API key is expected to be set in
    the environment variable `GEMINI_API_KEY`.

    :param input: Input parameters for the OCR task (config, input directory, date).
    :return: An `OcrTaskOutput` object containing the extracted menus.
    """
    with input.site_config_file.open('rt', encoding='utf-8') as f:
        site_data = yaml.safe_load(f)

    sites = [Restaurant.model_validate(rest_dict) for rest_dict in site_data['restaurants']]

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    ok_results = []
    err_results = []

    prompt = get_ocr_prompt(input.date)

    for site in sites:
        try:
            image = PIL.Image.open(input.in_dir / f'{site.id}.jpeg')
            LOG.info(f'Running OCR for {site.id}')

            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=[image, prompt],
                config=GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=ParsedMenu,
                    temperature=0.0
                ),
            )
            if not isinstance(response.parsed, ParsedMenu):
                err_msg = f'Unexpected response type: {type(response.parsed)}'
                raise ValueError(err_msg)

            ok_results.append(OcrResult(id=site.id, data=response.parsed))
        except Exception as e:
            LOG.error(f'Failed to extract menu for {site.id}: {type(e)}:{e}')
            err_results.append(ErrorResult(id=site.id, error=str(e)))

    return OcrTaskOutput(results=ok_results, errors=err_results, date=input.date)


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Parse screenshots of webpages')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--in-dir', required=True, help='Path to input directory')
    parser.add_argument('--out-file', required=True, help='Path to output file')
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv('GEMINI_API_KEY'):
        raise ValueError('GEMINI_API_KEY is not set')

    result = await ocr_task(OcrTaskInput(
        site_config_file=Path(args.sites),
        in_dir=Path(args.in_dir)
    ))

    out_file = Path(args.out_file).resolve()
    LOG.info(f'Writing output to {out_file}')
    Path(out_file).write_text(result.model_dump_json(indent=2), encoding='utf-8')


if __name__ == "__main__":
    asyncio.run(main())
