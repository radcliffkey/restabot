import datetime
from pathlib import Path
from typing import Literal

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
    out_dir: Path
    date: datetime.date = Field(default_factory=lambda: datetime.date.today())


class ScreenshotResult(BaseModel):
    id: str
    path: Path


class ScreenshotTaskOutput(BaseModel):
    results: list[ScreenshotResult]
    errors: list[ErrorResult]


class Meal(BaseModel):
    name: str = Field(description='Name of the meal in Czech language')
    description: str | None = Field(description='Additional information about the meal.')
    is_vegetarian: bool
    price: str


class DailyMenu(BaseModel):
    day: str = Field(description='Date or day of the week, depending on what can be extracted.')
    meals: list[Meal] = Field(description='List of meals for the day. Leave empty if no meals were provided.')


class ParsedMenu(BaseModel):
    message: str = Field(description='Message summarizing if the extraction was successful.')
    daily_menus: list[DailyMenu] = Field(
        description='List of menus for each day. It is possible that there is only one day mentioned.')


class OcrResult(BaseModel):
    id: str
    data: ParsedMenu


class OcrTaskOutput(BaseModel):
    results: list[OcrResult]
    errors: list[ErrorResult]
