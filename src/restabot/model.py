from pathlib import Path

from pydantic import BaseModel

class Restaurant(BaseModel):
    id: str
    name: str
    url: str

class ScreenshotTaskInput(BaseModel):
    site_config_file: Path
    out_dir: Path
