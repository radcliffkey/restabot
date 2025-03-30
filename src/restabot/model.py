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


class OcrResult(BaseModel):
    id: str
    data: str


class OcrTaskOutput(BaseModel):
    results: list[OcrResult]
    errors: list[ErrorResult]
