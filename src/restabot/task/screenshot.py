import argparse
import asyncio
import logging
from pathlib import Path
from typing import Literal

import yaml
from playwright.async_api import async_playwright

from restabot.model import ErrorResult, Restaurant, ScreenshotResult, ScreenshotTaskInput, ScreenshotTaskOutput
from restabot.util import parallel_process

LOG = logging.getLogger(f'{__package__}.screenshot')


async def _accept_cookies(page, site):
    cookie_accept_selectors = [
        "button:has-text('Přijmout')",
        "button:has-text('Consent')",
        "button:has-text('Accept')",
    ]
    for selector in cookie_accept_selectors:
        try:
            if await page.locator(selector=selector).count() > 0:
                LOG.info(f'{site.id} - Cookie selector matched: {selector}')
                await page.locator(selector=selector).click()
                break
        except Exception:
            continue


async def screenshot_site(
        site: Restaurant,
        out_dir: Path,
        format: Literal['jpeg', 'png'] | None = None,
        quality: int | None = None
) -> ScreenshotResult:
    async with async_playwright() as pw:

        LOG.info(f'{site.id} - launching browser')
        browser = await pw.firefox.launch()
        page = await browser.new_page()
        await page.goto(site.url)
        await page.wait_for_timeout(400)

        await _accept_cookies(page, site)

        await page.wait_for_timeout(200)

        LOG.info(f'{site.id} - taking screenshot')
        out_file = out_dir / f'{site.id}.{format}'
        await page.screenshot(path=out_file, full_page=True, type=format, quality=quality)
        await browser.close()

        return ScreenshotResult(id=site.id, path=out_file)


async def screenshot_task(input: ScreenshotTaskInput) -> ScreenshotTaskOutput:
    """
    Takes screenshots of all the websites in the site configuration file.

    The function takes a ScreenshotTaskInput object as an argument and returns a
    ScreenshotTaskOutput object. It loads the site configuration from the file,
    filters out non-http URLs, creates a directory for the screenshots if it
    doesn't exist, and then takes the screenshots. The screenshots are saved in the directory
    with the filename being the ID of the restaurant.

    :param input: Input parameters for the task (config file, output directory,
      image format, quality).
    :return: The results of the task, containing the paths to the screenshots and
      any errors that occurred.
    """
    LOG.info(f'Running screenshot task with {input.model_dump()}')

    with input.site_config_file.open('rt', encoding='utf-8') as f:
        site_data = yaml.safe_load(f)

    sites = [Restaurant.model_validate(rest_dict) for rest_dict in site_data['restaurants']]
    sites = [r for r in sites if r.url.startswith('http')]

    out_dir = input.out_dir
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
    elif not out_dir.is_dir():
        raise ValueError(f'{out_dir} is not a directory')

    out_dir = out_dir.resolve()

    async def make_screenshot(site):
        try:
            return await screenshot_site(site, out_dir=out_dir, format=input.format, quality=input.quality)
        except Exception as e:
            return ErrorResult(id=site.id, error=str(e))

    results = await parallel_process(sites, make_screenshot, max_concurrency=5)
    ok_results = []
    err_results = []

    for result in results:
        if isinstance(result, ScreenshotResult):
            ok_results.append(result)
        elif isinstance(result, ErrorResult):
            err_results.append(result)

    return ScreenshotTaskOutput(results=ok_results, errors=err_results)


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Take screenshots of a webpages')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--out-dir', required=True, help='Path to output directory')
    parser.add_argument('--out-format', choices=['jpeg', 'png'], default='png', help='Format of the output image')
    parser.add_argument(
        '--jpeg-quality', type=int,
        help='Quality of the output image (1-100). Applied only if out-format is jpeg'
    )

    args = parser.parse_args()

    result = await screenshot_task(ScreenshotTaskInput(
        site_config_file=Path(args.sites),
        out_dir=Path(args.out_dir),
        format=args.out_format,
        quality=args.jpeg_quality
    ))

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
