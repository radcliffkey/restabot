# Restabot

Restabot is a Python application that automates the process of fetching and summarizing restaurant menus.

## Installation

```
pip install {restabot_repo_dir}
playwright install
```

## Environment variables

For the pipeline to run, you will need to set the following environment variables:

- `GEMINI_API_KEY` - Google Gemini API key - Gemini is used for OCR and summarization
- `SLACK_BOT_TOKEN` - Token for posting to / downloading from Slack
- `SLACK_CHANNEL_ID` - Optional Slack channel to post to

If you store them in `.env` file, they will be automatically loaded.

## Data format

Restaurant data is stored in a YAML file.

```yaml
restaurants:
  - id: "restaurant1"
    name: "Restaurant 1"
    url: "https://restaurant1.com/daily-menu"
  - id: "restaurant2"
    name: "Restaurant 2"
    url: "slack://channel_id"
```

## Running the bot

Example of running the bot's pipeline - it makes screenshots, performs OCR on them, and generates a summary:

```
python -m restabot.pipeline \
    --sites data/restaurants.yaml \
    --screenshots-dir data/screenshots \
    --ocr-output data/parsed_menus.json \
    --summary-output data/summary.md
```

## Development

For development, install additional dependencies:
```bash
pip install -e ".[dev]"
```

This includes:
- pytest for testing
- flake8 for code style checking

### Core Components

- `pipeline`: Runs the entire menu fetching and processing pipeline
- `model`: Contains data models and configuration schemas using Pydantic

### Task Modules

The `restabot.task` package contains specialized modules for different stages of menu processing:

- `screenshot`: Captures screenshots of restaurant menu pages using Playwright
- `ocr`: Performs optical character recognition on menu images
- `summary`: Generates menu summaries using Google's Gemini AI
- `slack_upload`: Handles posting the processed menus to Slack
- `slack_download`: Limited support for dowloading menus from Slack - downloads the latest image posted to given channel

### Dependencies

Key dependencies include:
- Playwright for web automation and screenshot capture
- Google Gemini AI for menu text analysis and summarization
- Slack SDK for posting results
- Pydantic for data validation and settings management
- PyYAML for configuration file parsing
