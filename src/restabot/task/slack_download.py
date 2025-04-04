import argparse
import asyncio
import datetime
import logging
import os

from pathlib import Path

import aiohttp
import yaml
from dotenv import load_dotenv
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from restabot.model import ErrorResult, Restaurant, ScreenshotResult, SlackDownloadTaskInput, SlackDownloadTaskOutput

LOG = logging.getLogger(f'{__package__}.slack_download')


async def slack_download_task(input: SlackDownloadTaskInput) -> SlackDownloadTaskOutput:
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

    ok_results = []
    err_results = []

    for site in sites:
        try:
            channel_id = site.url.removeprefix('slack://')
            LOG.info(f'Downloading last image from Slack channel {channel_id}')
            now = int(datetime.datetime.now().timestamp())
            yesterday = now - 24 * 60 * 60
            resp = await client.conversations_history(channel=channel_id, oldest=yesterday)

            if 'messages' not in resp or not resp['messages']:
                error_msg = f'No messages found in channel {channel_id}'
                LOG.error(error_msg)
                err_results.append(ErrorResult(id=site.id, error=error_msg))
                continue

            file_msgs = [msg for msg in resp['messages'] if 'files' in msg]
            last_msg = max(file_msgs, key=lambda msg: msg['ts'])
            download_url = last_msg['files'][0]['url_private_download']
            out_file = out_dir / f'{site.id}.{download_url.split('.')[-1]}'

            LOG.info('Downloading file from channel {channel_id}')
            headers = {'Authorization': f'Bearer {os.getenv("SLACK_BOT_TOKEN")}'}
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url, headers=headers) as file_response:
                    if file_response.status == 200:
                        with open(out_file, 'wb') as f:
                            async for chunk in file_response.content.iter_chunked(8192):
                                f.write(chunk)
                        LOG.info(f"Successfully downloaded a photo to '{out_file}'")
                        ok_results.append(ScreenshotResult(id=site.id, path=out_file))
                    else:
                        error_msg = f'Failed to download photo. Status code: {file_response.status}'
                        LOG.error(error_msg)
                        err_results.append(ErrorResult(id=site.id, error=error_msg))

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

    result = await slack_download_task(SlackDownloadTaskInput(
        site_config_file=Path(args.sites),
        out_dir=Path(args.out_dir)
    ))

    print(result.model_dump_json(indent=2))


if __name__ == '__main__':
    asyncio.run(main())
