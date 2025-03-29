import argparse
import asyncio
import logging
import typing
from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path

import yaml
from playwright.async_api import async_playwright

from restabot.model import Restaurant, ScreenshotTaskInput

R = typing.TypeVar('R')
T = typing.TypeVar('T')

LOG = logging.getLogger(f'{__package__}.screenshot')

async def screenshot_site(site: Restaurant, out_dir: Path):
    async with async_playwright() as pw:

        LOG.info(f'{site.id} - launching browser')
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(site.url)
        await page.wait_for_timeout(200)

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
            except:
                continue

        await page.wait_for_timeout(200)

        LOG.info(f'{site.id} - taking screenshot')
        await page.screenshot(path=out_dir / f'{site.id}.jpeg', full_page=True, type='jpeg', quality=80)
        await browser.close()

async def parallel_process(
        items: Iterable[T],
        afunc: Callable[[T], Awaitable[R]],
        max_concurrency: int
) -> list[R]:
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = []

    async def process_item_with_semaphore(item):
        async with semaphore:
            return await afunc(item)

    for item in items:
        task = asyncio.create_task(process_item_with_semaphore(item))
        tasks.append(task)

    return await asyncio.gather(*tasks)

async def screenshot_task(input: ScreenshotTaskInput):
    with input.site_config_file.open('rt', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    out_dir = input.out_dir
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
    elif not out_dir.is_dir():
        raise ValueError(f'{out_dir} is not a directory')

    sites = [Restaurant.model_validate(rest_dict) for rest_dict in data['restaurants']]

    async def make_screenshot(site):
        return await screenshot_site(site, out_dir=out_dir)

    await parallel_process(sites, make_screenshot, max_concurrency=5)


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Take screenshots of a webpages')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--out-dir', required=True, help='Path to output directory')
    args = parser.parse_args()

    await screenshot_task(ScreenshotTaskInput(
        site_config_file=Path(args.sites),
        out_dir=Path(args.out_dir)
    ))


if __name__ == "__main__":
    asyncio.run(main())
