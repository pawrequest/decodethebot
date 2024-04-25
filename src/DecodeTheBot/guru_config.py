import functools
import os
from pathlib import Path

from pydantic import HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from suppawt.pawlogger import get_loguru

GURU_ENV = os.getenv('GURU_ENV')
REDDIT_ENV = os.getenv('REDDIT_ENV')
print(GURU_ENV, REDDIT_ENV)
if not GURU_ENV or not Path(GURU_ENV).exists():
    raise ValueError('GURU_ENV (path to environment file) not set')
if not REDDIT_ENV or not Path(REDDIT_ENV).exists():
    raise ValueError('REDDIT_ENV (path to environment file) not set')


class RedditConfig(BaseSettings):
    refresh_token: str
    client_id: str
    client_secret: str
    user_agent: str

    custom_flair_id: str | None = None
    redirect_uri: str

    send_key: str

    subreddit_name: str = 'test'
    wiki_name: str = 'test'

    model_config = SettingsConfigDict(env_ignore_empty=True, env_file=REDDIT_ENV, extra='ignore')


class GuruConfig(BaseSettings):
    backup_dir: Path
    guru_names_file: Path
    guru_db: Path
    log_file: Path
    podcast_url: HttpUrl
    backup_shelf: Path | None = None

    @model_validator(mode='after')
    def backup_shelf(self):
        if self.backup_shelf is None:
            self.backup_shelf = Path(self.backup_dir / 'dtg_bot.shelf')
        return self

    page_size: int = 20

    backup_sleep: int = 60 * 60 * 24
    scraper_sleep: int = 60 * 10
    reddit_sleep: int = 60 * 10

    init_eps: bool = False
    restore_from_shelf: bool = False
    max_dupes: int = 5
    debug: bool = False
    trim_db: bool = False
    episode_scrape_limit: int | None = None

    model_config = SettingsConfigDict(env_ignore_empty=True, env_file=GURU_ENV)


logger_dict = {
    'Scraper': 'cyan',
    'Monitor': 'green',
    'Backup': 'magenta',
}


@functools.lru_cache
def guru_settings():
    cf = GuruConfig()
    logger = get_loguru(cf.log_file, 'local', category_dict=logger_dict)
    logger.info(f'GuruConfig loaded from {GURU_ENV}')
    logger.info(f'RedditConfig loaded from {REDDIT_ENV}')
    return cf


@functools.lru_cache
def reddit_settings():
    return RedditConfig()


if __name__ == '__main__':
    gs = guru_settings()
    rs = reddit_settings()
    ...
