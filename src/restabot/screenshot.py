import argparse
import asyncio
import logging
import typing
from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path
from typing import Literal

import yaml
from playwright.async_api import async_playwright

from restabot.model import ErrorResult, Restaurant, ScreenshotResult, ScreenshotTaskInput, ScreenshotTaskOutput

R = typing.TypeVar('R')
T = typing.TypeVar('T')

LOG = logging.getLogger(f'{__package__}.screenshot')


async def screenshot_site(
        site: Restaurant,
        out_dir: Path,
        format: Literal['jpeg', 'png'] | None = None,
        quality: int | None = None
) -> ScreenshotResult:
    async with async_playwright() as pw:

        LOG.info(f'{site.id} - launching browser')
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(site.url)
        await page.wait_for_timeout(300)

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
        out_file = out_dir / f'{site.id}.{format}'
        await page.screenshot(path=out_file, full_page=True, type=format, quality=quality)
        await browser.close()

        return ScreenshotResult(id=site.id, path=out_file)


async def parallel_process(
        items: Iterable[T],
        afunc: Callable[[T], Awaitable[R]],
        max_concurrency: int
) -> list[R | Exception]:
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = []

    async def process_item_with_semaphore(item):
        async with semaphore:
            return await afunc(item)

    for item in items:
        task = asyncio.create_task(process_item_with_semaphore(item))
        tasks.append(task)

    return await asyncio.gather(*tasks, return_exceptions=True)


async def screenshot_task(input: ScreenshotTaskInput) -> ScreenshotTaskOutput:
    LOG.info(f'Running screenshot task with {input.model_dump()}')

    with input.site_config_file.open('rt', encoding='utf-8') as f:
        site_data = yaml.safe_load(f)

    sites = [Restaurant.model_validate(rest_dict) for rest_dict in site_data['restaurants']]

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
