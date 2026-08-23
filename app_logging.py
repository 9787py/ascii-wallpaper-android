"""Small persistent logger usable before the Kivy UI is fully available."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def configure(data_directory):
    log_dir = Path(data_directory) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "ascii-wallpaper.log"
    handlers = [RotatingFileHandler(
        log_path, maxBytes=1024 * 1024, backupCount=2, encoding="utf-8")]
    if sys.stderr:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    return log_path
