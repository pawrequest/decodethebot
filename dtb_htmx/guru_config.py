from pathlib import Path

from pydantic_settings import BaseSettings
from suppawt.pawlogger import get_loguru


class GuruConfig(BaseSettings):
    page_size: int = 20

    podcast_url: str
    subreddit_name: str = "test"

    restore_from_json: bool = False
    backup_dir: Path = "backups"
    backup_json: Path = "backups/guru_backup.json"
    guru_names_file: str = "gurunames.txt"
    log_file: Path = "guru_log.log"

    backup_sleep: int = 60 * 60 * 24
    scraper_sleep: int = 60 * 10
    reddit_sleep: int = 60 * 10

    init_eps: bool = False
    max_dupes: int = 0
    debug: bool = False
    trim_db: bool = False
    episode_scrape_limit: int = None


logger_dict = {
    'Scraper': 'cyan',
    'Monitor': 'green',
    'Backup': 'magenta',
}

guru_settings = GuruConfig()
logger = get_loguru(guru_settings.log_file, "local", category_dict=logger_dict)
