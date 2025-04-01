import argparse
import asyncio
import logging
import os
from pathlib import Path

import PIL.Image
import yaml
from dotenv import load_dotenv
from google import genai

from restabot.model import ErrorResult, OcrResult, OcrTaskInput, OcrTaskOutput, ParsedMenu, Restaurant

LOG = logging.getLogger(f'{__package__}.ocr')


OCR_PROMPT = (
    'Extract daily menus from the image. The text is in Czech language. '
    'If the menus cannot be extracted, please respond with an error message '
    'and leave `daily_menus` field empty.'
)


async def ocr_task(input: OcrTaskInput) -> OcrTaskOutput:
    with input.site_config_file.open('rt', encoding='utf-8') as f:
        site_data = yaml.safe_load(f)

    sites = [Restaurant.model_validate(rest_dict) for rest_dict in site_data['restaurants']]

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    ok_results = []
    err_results = []

    for site in sites:
        image = PIL.Image.open(input.in_dir / f'{site.id}.jpeg')
        LOG.info(f'Running OCR for {site.id}')
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[image, OCR_PROMPT],
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': ParsedMenu,
                },
            )
            assert isinstance(response.parsed, ParsedMenu)
            ok_results.append(OcrResult(id=site.id, data=response.parsed))
        except Exception as e:
            LOG.error(f'Failed to extract menu for {site.id}: {e}')
            err_results.append(ErrorResult(id=site.id, error=str(e)))
            continue

    return OcrTaskOutput(results=ok_results, errors=err_results)


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
