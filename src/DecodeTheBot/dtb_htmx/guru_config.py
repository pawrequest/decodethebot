import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from suppawt.pawlogger import get_loguru

GURU_ENV = os.getenv('GURU_ENV')
if not Path(GURU_ENV).exists():
    raise ValueError('GURU_ENV (path to environment file) not set')


class GuruConfig(BaseSettings):
    page_size: int = 20

    podcast_url: str
    subreddit_name: str = 'test'

    restore_from_json: bool = False
    backup_dir: Path = 'backups'
    backup_json: Path = 'backups/guru_backup.json'
    guru_names_file: str = 'gurunames.txt'
    log_file: Path = 'guru_log.log'

    backup_sleep: int = 60 * 60 * 24
    scraper_sleep: int = 60 * 10
    reddit_sleep: int = 60 * 10

    init_eps: bool = False
    max_dupes: int = 0
    debug: bool = False
    trim_db: bool = False
    episode_scrape_limit: int | None = None

    model_config = SettingsConfigDict(env_ignore_empty=True, env_file=GURU_ENV, extra='ignore')


logger_dict = {
    'Scraper': 'cyan',
    'Monitor': 'green',
    'Backup': 'magenta',
}

guru_settings = GuruConfig()
logger = get_loguru(guru_settings.log_file, 'local', category_dict=logger_dict)
