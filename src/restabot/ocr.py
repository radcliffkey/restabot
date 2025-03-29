import argparse
import asyncio
import logging
from pathlib import Path

import yaml

from restabot.model import OcrTaskInput, OcrTaskOutput, Restaurant

LOG = logging.getLogger(f'{__package__}.ocr')


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

    LOG.warning('OCR not implemented yet')

    return OcrTaskOutput(results=[], errors=[])


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Parse screenshots of webpages')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--in-dir', required=True, help='Path to input directory')
    parser.add_argument('--out-dir', required=True, help='Path to output directory')
    args = parser.parse_args()

    await ocr_task(OcrTaskInput(
        site_config_file=Path(args.sites),
        in_dir=Path(args.in_dir),
        out_dir=Path(args.out_dir)
    ))


if __name__ == "__main__":
    asyncio.run(main())
