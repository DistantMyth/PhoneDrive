import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def configure_logging():
    directory = Path(os.environ.get("APPDATA", ".")) / "PhoneDrive"
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / "phonedrive.log", maxBytes=1_000_000,
                                  backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
