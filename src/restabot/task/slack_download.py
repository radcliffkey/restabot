import argparse
import asyncio
import datetime
import logging
import os
from pathlib import Path
from typing import Any, cast

import aiohttp
import yaml
from dotenv import load_dotenv
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from restabot.model import ErrorResult, Restaurant, ScreenshotResult, SlackDownloadTaskInput, SlackDownloadTaskOutput

LOG = logging.getLogger(f'{__package__}.slack_download')


async def _download_file(url: str, out_file: Path) -> None:
    headers = {'Authorization': f'Bearer {os.getenv("SLACK_BOT_TOKEN")}'}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as file_response:
            file_response.raise_for_status()
            with open(out_file, 'wb') as f:
                async for chunk in file_response.content.iter_chunked(8192):
                    f.write(chunk)


async def slack_download_task(input: SlackDownloadTaskInput) -> SlackDownloadTaskOutput:
    """
    Download the last image from a Slack channel for restaurants configured with `slack://` URL.
    :param input: task input (config, output directory)
    :return: output structure with the paths to the downloaded images and any errors that occurred
    """
    with input.site_config_file.open('rt', encoding='utf-8') as f:
        site_data = yaml.safe_load(f)

    sites = [Restaurant.model_validate(rest_dict) for rest_dict in site_data['restaurants']]
    sites = [r for r in sites if r.url.startswith('slack://')]

    out_dir = input.out_dir
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
    elif not out_dir.is_dir():
        raise ValueError(f'{out_dir} is not a directory')

    out_dir = out_dir.resolve()

    client = AsyncWebClient(token=os.getenv('SLACK_BOT_TOKEN'))

    ok_results: list[ScreenshotResult] = []
    err_results: list[ErrorResult] = []

    for site in sites:
        channel_id = site.url.removeprefix('slack://')
        try:
            LOG.info(f'Downloading last image from Slack channel {channel_id}')
            now = int(datetime.datetime.now().timestamp())
            yesterday = now - 24 * 60 * 60
            # slack_sdk stubs use **kwargs: Unknown on API methods
            resp = await client.conversations_history(channel=channel_id, oldest=str(yesterday))  # pyright: ignore[reportUnknownMemberType]

            messages = cast(list[dict[str, Any]], resp.get('messages') or [])
            if not messages:
                error_msg = f'No messages found in channel {channel_id}'
                LOG.error(error_msg)
                err_results.append(ErrorResult(id=site.id, error=error_msg))
                continue

            file_msgs = [msg for msg in messages if 'files' in msg]
            if not file_msgs:
                error_msg = f'No file messages found in channel {channel_id}'
                LOG.error(error_msg)
                err_results.append(ErrorResult(id=site.id, error=error_msg))
                continue

            last_msg = max(file_msgs, key=lambda msg: str(msg['ts']))
            files = cast(list[dict[str, Any]], last_msg['files'])
            if not files or 'url_private_download' not in files[0]:
                error_msg = f'No downloadable file found in channel {channel_id}'
                LOG.error(error_msg)
                err_results.append(ErrorResult(id=site.id, error=error_msg))
                continue

            download_url = str(files[0]['url_private_download'])
            ext = download_url.split('.')[-1]
            if ext == 'jpg':
                ext = 'jpeg'
            out_file = out_dir / f'{site.id}.{ext}'

            try:
                await _download_file(download_url, out_file)
                LOG.info(f"Successfully downloaded a photo to '{out_file}'")
                ok_results.append(ScreenshotResult(id=site.id, path=out_file))
            except Exception as e:
                error_msg = f'Failed to download last image: {str(e)}'
                LOG.error(error_msg)
                err_results.append(ErrorResult(id=site.id, error=error_msg))
                continue

        except SlackApiError as e:
            LOG.error(f'Failed to download last image from Slack channel {channel_id}: {e.response["error"]}')
            err_results.append(ErrorResult(id=site.id, error=f'Failed to download last image: {e.response["error"]}'))
            continue
        except Exception as e:
            error_msg = f'Unexpected error while posting to Slack: {str(e)}'
            LOG.error(error_msg)
            err_results.append(ErrorResult(id=site.id, error=error_msg))

    return SlackDownloadTaskOutput(results=ok_results, errors=err_results)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Download menu photos from Slack')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--out-dir', required=True, help='Path to output directory')
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv('SLACK_BOT_TOKEN'):
        raise ValueError('SLACK_BOT_TOKEN is not set')

    result = await slack_download_task(
        SlackDownloadTaskInput(site_config_file=Path(args.sites), out_dir=Path(args.out_dir))
    )

    print(result.model_dump_json(indent=2))


if __name__ == '__main__':
    asyncio.run(main())
