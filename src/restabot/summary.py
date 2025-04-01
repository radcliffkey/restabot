import argparse
import asyncio
import datetime
import json
import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from google import genai

from restabot.model import DailySummary, OcrTaskOutput, Restaurant, SummaryTaskInput, SummaryTaskOutput

LOG = logging.getLogger(f'{__package__}.summary')


SUMMARY_PROMPT_TMPL = (
    'Please analyze the following restaurant menus and create a listing.'
    '- Select only menus for {date} ({day_of_week}). If the menu applies to the whole current week, include it.\n'
    '- Create a listing written in Czech language\n'
    '- Do not omit any meals, but correct spelling and duplicates\n'
    '- Arrange the information in common format:'
    ' <meal name and description, capitalized but not all caps> – <price> Kč. Omit the price if it is unknown.\n'
    '- Prefix vegetarian dishes with 🌿 emoji.\n'
    '- Prefix non-vegetarian dishes with a suitable emoji for given dish. Be creative!\n'
    '- Use Markdown format: headings, bullet points, etc.\n'
    'Use `thinking` field for planning your next steps and reasoning. '
    'The input is in JSON format and was automatically extracted by OCR; it can contain errors.\n\n'
    'Restaurant menus:\n\n'
    '{menus}'
)


def get_summary_prompt(date: datetime.date, menus: list[dict]) -> str:
    day_of_week = date.strftime('%A')  # Get full day name in English
    menus_text = '\n\n'.join(json.dumps(menu, indent=2, ensure_ascii=False) for menu in menus)
    return SUMMARY_PROMPT_TMPL.format(date=date.isoformat(), day_of_week=day_of_week, menus=menus_text)


async def summary_task(input: SummaryTaskInput) -> SummaryTaskOutput:
    with input.site_config_file.open('rt', encoding='utf-8') as f:
        site_data = yaml.safe_load(f)
    restaurants = {r['id']: Restaurant.model_validate(r) for r in site_data['restaurants']}

    ocr_output = OcrTaskOutput.model_validate_json(input.ocr_output_file.read_text(encoding='utf-8'))

    menus = []
    for result in ocr_output.results:
        restaurant = restaurants[result.id]
        menus.append({
            'name': restaurant.name,
            'menus': result.data.model_dump()['daily_menus'],
        })

    if not menus:
        return SummaryTaskOutput(
            summary=DailySummary(text='No menus available for analysis.', thinking=''),
            date=ocr_output.date
        )

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    prompt = get_summary_prompt(ocr_output.date, menus)

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': DailySummary,
                'temperature': 0.0
            },
        )
        assert isinstance(response.parsed, DailySummary)
        return SummaryTaskOutput(summary=response.parsed, date=ocr_output.date)
    except Exception as e:
        LOG.error(f'Failed to generate summary: {e}')
        return SummaryTaskOutput(
            summary=DailySummary(text=f'Error generating summary: {str(e)}', thinking=''),
            date=ocr_output.date
        )


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Generate summary of restaurant menus')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--ocr-output', required=True, help='Path to OCR output file')
    parser.add_argument('--out-file', required=True, help='Path to output file')
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv('GEMINI_API_KEY'):
        raise ValueError('GEMINI_API_KEY is not set')

    result = await summary_task(SummaryTaskInput(
        site_config_file=Path(args.sites),
        ocr_output_file=Path(args.ocr_output)
    ))

    out_file = Path(args.out_file).resolve()
    LOG.info(f'Thinking:\n{result.summary.thinking}')
    LOG.info(f'Writing output to {out_file}')
    Path(out_file).write_text(result.summary.text, encoding='utf-8')


if __name__ == "__main__":
    asyncio.run(main())
