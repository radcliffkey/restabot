import datetime
from pathlib import Path
from typing import Literal, Union

from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    id: str
    name: str
    url: str


class ErrorResult(BaseModel):
    id: str
    error: str


class ScreenshotTaskInput(BaseModel):
    site_config_file: Path
    out_dir: Path
    format: Literal['jpeg', 'png']
    quality: int | None = None


class OcrTaskInput(BaseModel):
    site_config_file: Path
    in_dir: Path
    date: datetime.date = Field(default_factory=lambda: datetime.date.today())


class ScreenshotResult(BaseModel):
    id: str
    path: Path


class ScreenshotTaskOutput(BaseModel):
    results: list[ScreenshotResult]
    errors: list[ErrorResult]

class SlackDownloadTaskInput(BaseModel):
    site_config_file: Path
    out_dir: Path


SlackDownloadTaskOutput = ScreenshotTaskOutput


class Dish(BaseModel):
    name: str = Field(description='Name of the dish in Czech language')
    description: str | None = Field(
        description='Additional information about the dish (written in Czech or English).'
                    'Usually contains ingredients, English translation etc.')
    is_vegetarian: bool = Field(description='Indicates if the dish is vegetarian. (Cheese is vegetarian.)')
    price: int | None = Field(description='Price of the dish in local currency.')


class SimpleDate(BaseModel):
    day: int
    month: int

class DateRange(BaseModel):
    start: SimpleDate
    end: SimpleDate

DayOfWeek = Literal['pondělí', 'úterý', 'strěda', 'čtvrtek', 'pátek', 'sobota', 'neděle']

class DailyMenu(BaseModel):
    day: Union[SimpleDate, DateRange, DayOfWeek, Literal['whole_week']] = Field(
        description='depending on menu type, this field will contain one of the following:\n'
                    '- date\n'
                    '- day of week\n'
                    '- date range if the menu is weekly\n'
                    '- "whole_week" if the menu is weekly and the date range is not available'
    )
    dishes: list[Dish] = Field(
        description='List of dishes for the day/week. Leave empty if no dishes were provided. Do not include drinks.'
    )


class ParsedMenu(BaseModel):
    languages: list[str] = Field(
        description='List of languages detected in the text. Most likely languages are Czech and English. '
                    'Take the language into account when parsing the text.')
    daily_menus: list[DailyMenu] = Field(
        description='List of menus for each day. It is possible that there is only one day mentioned.')


class OcrResult(BaseModel):
    id: str
    data: ParsedMenu


class OcrTaskOutput(BaseModel):
    results: list[OcrResult]
    errors: list[ErrorResult]
    date: datetime.date


class SummaryTaskInput(BaseModel):
    site_config_file: Path
    ocr_output_file: Path


class DailySummary(BaseModel):
    reasoning: str = Field(description='Step-by-step planning and reasoning.')
    text: str = Field(description='Listing of the daily menus in Czech language. Use concise Markdown format.')


class SummaryTaskOutput(BaseModel):
    summary: DailySummary
    date: datetime.date


class SlackUploadTaskInput(BaseModel):
    site_config_file: Path
    channel_id: str
    summary_file: Path


class SlackUploadTaskOutput(BaseModel):
    error: str | None = Field(description='Error message if the upload failed.')
