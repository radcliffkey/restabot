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


class OcrTaskInput(BaseModel):
    site_config_file: Path
    in_dir: Path
    date: datetime.date = Field(default_factory=lambda: datetime.date.today())


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


class DayOfWeek(BaseModel):
    day_name: Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] = Field(
        description='Name of the day in English.'
    )


class DailyMenu(BaseModel):
    valid_for_text: str | None = Field(
        description='Day(s) for which the menu is valid. '
                    'Do not include hours and minutes (HH:MM). '
                    'Leave empty if the day(s) are not in the text.'
    )
    valid_for: Union[SimpleDate, DateRange, DayOfWeek, Literal['whole_week']] | None = Field(
        description='Day(s) for which the menu is valid. '
                    'Depending on input text and menu type, '
                    'this field will contain one of the following:\n'
                    '- date; parse `XX.YY` as `XX` = day and `YY` = month\n'
                    '- date range if the menu is weekly\n'
                    '- day of week\n'
                    '- "whole_week" if the menu is weekly or the date range is not available'
                    '- null if no date-related information is available'
    )
    dishes: list[Dish] = Field(
        description='List of dishes for the day/week. Leave empty if no dishes were provided. Do not include drinks.'
    )


class ParsedMenu(BaseModel):
    languages: list[str] = Field(
        description='List of languages detected in the text. Most likely languages are Czech and English. '
                    'Take the language into account when parsing the text.')
    daily_menus: list[DailyMenu] = Field(
        description='List of daily/weekly menus. If the text does not contain any menus, leave this field empty.')


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
