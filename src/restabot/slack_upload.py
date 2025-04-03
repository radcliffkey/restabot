import argparse
import asyncio
import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from restabot.model import SlackUploadTaskInput, SlackUploadTaskOutput

LOG = logging.getLogger(f'{__package__}.slack_upload')


async def slack_upload_task(input: SlackUploadTaskInput) -> SlackUploadTaskOutput:
    with input.site_config_file.open('rt', encoding='utf-8') as f:
        yaml.safe_load(f)

    summary_text = input.summary_file.read_text(encoding='utf-8')

    client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))

    try:
        client.chat_postMessage(
            channel=input.channel_id,
            text=summary_text,
            blocks=[
                {'type': 'markdown', 'text': summary_text}
            ]
        )
        LOG.info(f'Successfully posted message to Slack channel {input.channel_id}')
        return SlackUploadTaskOutput(error=None)
    except SlackApiError as e:
        error_msg = f'Error posting message to Slack: {e.response["error"]}'
        LOG.error(error_msg)
        return SlackUploadTaskOutput(error=error_msg)
    except Exception as e:
        error_msg = f'Unexpected error while posting to Slack: {str(e)}'
        LOG.error(error_msg)
        return SlackUploadTaskOutput(error=error_msg)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Upload menu summary to Slack')
    parser.add_argument('--sites', required=True, help='Path to YAML file containing restaurant website data')
    parser.add_argument('--summary-file', required=True, help='Path to the daily menu summary file to upload')
    parser.add_argument(
        '--channel-id',
        help='Slack channel ID to post to. If not provided, the SLACK_CHANNEL_ID environment variable will be used.'
    )
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv('SLACK_BOT_TOKEN'):
        raise ValueError('SLACK_BOT_TOKEN is not set')

    channel_id = args.channel_id or os.getenv('SLACK_CHANNEL_ID')
    if not channel_id:
        LOG.error(
            'Slack channel ID is not set. Either pass it as an argument '
            'or set the SLACK_CHANNEL_ID environment variable.'
        )
        exit(1)

    result = await slack_upload_task(SlackUploadTaskInput(
        site_config_file=Path(args.sites),
        channel_id=channel_id,
        summary_file=Path(args.summary_file)
    ))

    if result.error:
        LOG.error(f'Failed to upload to Slack: {result.error}')
        exit(1)
    else:
        LOG.info('Successfully uploaded to Slack')


if __name__ == '__main__':
    asyncio.run(main())
