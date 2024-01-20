from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pawsupport import get_logger

logger = get_logger("/data/logs/guru_log.log", "local")

load_dotenv()
PAGE_SIZE = int(os.environ.get("PAGE_SIZE", 20))
SUBREDDIT_NAME = os.environ.get("SUBREDDIT_NAME", "test")
BACKUP_SLEEP = os.environ.get("BACKUP_SLEEP", 60 * 60 * 24)
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "backups"))
# RESTORE_FROM_JSON = bool(os.environ.get("RESTORE_FROM_JSON", False))
RESTORE_FROM_JSON = os.environ.get("RESTORE_FROM_JSON", "False").lower() == "true"
BACKUP_JSON = Path(os.environ.get("BACKUP_JSON", BACKUP_DIR / "guru_backup.json"))
PODCAST_URL = os.environ.get("PODCAST_URL_GURU")
if not PODCAST_URL:
    raise ValueError("PODCAST_URL must be provided")
GURU_NAMES_FILE = Path(os.environ.get("GURU_NAMES_FILE", "gurunames.txt"))
SCRAPER_SLEEP = int(os.environ.get("SCRAPER_SLEEP", 60 * 10))
INIT_EPS = int(os.environ.get("INIT_EPS", 0))
MAX_DUPES = 3
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
TRIM_DB = os.environ.get("TRIM_DB", "False").lower() == "true"
