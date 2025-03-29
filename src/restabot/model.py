import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    id: str
    name: str
    url: str


class ScreenshotTaskInput(BaseModel):
    site_config_file: Path
    out_dir: Path


class OcrTaskInput(BaseModel):
    site_config_file: Path
    in_dir: Path
    out_dir: Path
    date: datetime.date = Field(default_factory=lambda: datetime.date.today())


class OcrResult(BaseModel):
    id: str
    data: str

class OcrTaskOutput(BaseModel):
    results: list[OcrResult]
