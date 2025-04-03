import argparse
import asyncio
import datetime
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from restabot.model import OcrTaskInput, ScreenshotTaskInput, SummaryTaskInput
from restabot.task.ocr import ocr_task
from restabot.task.screenshot import screenshot_task
from restabot.task.summary import summary_task

LOG = logging.getLogger(f'{__package__}.pipeline')


async def run_pipeline(
    site_config_file: Path,
    screenshots_dir: Path,
    ocr_output_file: Path,
    summary_output_file: Path,
    date: datetime.date | None = None,
) -> None:
    """Run the complete pipeline: screenshot -> OCR -> summary."""
    if date is None:
        date = datetime.date.today()

    LOG.info('Taking screenshots...')
    screenshot_result = await screenshot_task(ScreenshotTaskInput(
        site_config_file=site_config_file,
        out_dir=screenshots_dir,
        format='jpeg',
        quality=90
    ))

    if screenshot_result.errors:
        LOG.warning(f'Screenshot errors: {screenshot_result.errors}')

    LOG.info('Running OCR...')
    ocr_result = await ocr_task(OcrTaskInput(
        site_config_file=site_config_file,
        in_dir=screenshots_dir,
        date=date
    ))

    if ocr_result.errors:
        LOG.warning(f'OCR errors: {ocr_result.errors}')

    ocr_output_file.write_text(ocr_result.model_dump_json(indent=2), encoding='utf-8')

    LOG.info('Generating summary...')
    summary_result = await summary_task(SummaryTaskInput(
        site_config_file=site_config_file,
        ocr_output_file=ocr_output_file
    ))

    summary_output_file.write_text(summary_result.summary.text, encoding='utf-8')
    LOG.info(f'Summary saved to {summary_output_file}')


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Run the complete pipeline: screenshot -> OCR -> summary')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--screenshots-dir', required=True, help='Directory to store screenshots')
    parser.add_argument('--ocr-output', required=True, help='Path to OCR output file')
    parser.add_argument('--summary-output', required=True, help='Path to summary output file')
    parser.add_argument('--date', help='Date to process (YYYY-MM-DD). Defaults to today.')
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv('GEMINI_API_KEY'):
        raise ValueError('GEMINI_API_KEY is not set')

    date = datetime.date.today()
    if args.date:
        date = datetime.date.fromisoformat(args.date)

    await run_pipeline(
        site_config_file=Path(args.sites),
        screenshots_dir=Path(args.screenshots_dir),
        ocr_output_file=Path(args.ocr_output),
        summary_output_file=Path(args.summary_output),
        date=date
    )


if __name__ == '__main__':
    asyncio.run(main())
