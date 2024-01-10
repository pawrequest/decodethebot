# todo make this not be in docker so no rebuild to edit
# from __future__ import annotations
from __future__ import annotations

import os
import shutil
import tomllib
from pathlib import Path
from typing import TypeVar, Union, TYPE_CHECKING

import dotenv

from gurupod.core.logger_config import get_logger

if TYPE_CHECKING:
    ...

dotenv.load_dotenv()

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent.parent
DATA_DIR = PROJECT_ROOT / os.environ.get("DATA_DIR", "data")
LOG_DIR = DATA_DIR / os.environ.get("LOG_DIR", "log")
LOG_FILENAME = LOG_DIR / os.environ.get("LOG_FILE", "gurulog.log")
LOG_PATH = LOG_DIR / LOG_FILENAME
CONFIG_FILENAME = os.environ.get("CONFIG_FILE", "guruconfig.toml")
CONFIG_PATH = DATA_DIR / CONFIG_FILENAME
LOG_PROFILE = os.environ.get("LOG_PROFILE")

logger = get_logger(log_file=LOG_PATH, profile=LOG_PROFILE)


def get_config(config_toml, default_config_toml, data_dir):
    if config_toml.exists():
        with open(config_toml, "rb") as f:
            guru_conf = tomllib.load(f)
            logger.info(f"Loaded config from {config_toml}", bot_name="BOOT")

    else:
        with open(default_config_toml, "rb") as f:
            guru_conf = tomllib.load(f)
            logger.info(f"Loaded default config from {default_config_toml}", bot_name="BOOT")
            logger.info(
                f"Initialising with default values:\n{[f"{k} = {v}" for k, v in guru_conf.items()]}", bot_name="BOOT"
            )
            Path.mkdir(data_dir, exist_ok=True)
            shutil.copy(default_config_toml, config_toml)

    return guru_conf


default_config = HERE / "config_default.toml"

guru_conf = get_config(CONFIG_PATH, default_config, DATA_DIR)

# reddits
SUB_TO_MONITOR = guru_conf.get("sub_to_monitor")
SUB_TO_POST = guru_conf.get("sub_to_post")
SUB_TO_WIKI = guru_conf.get("sub_to_wiki")
WIKI_TO_WRITE = guru_conf.get("wiki_page")
SUB_TO_TEST = guru_conf.get("sub_to_test")

GURU_FLAIR_ID = guru_conf.get("custom_flair")
DM_ADDRESS = guru_conf.get("dm_address")
HTML_TITLE = guru_conf.get("html_page_title")
# LOGGER_MATCH_STR = 'logger\.(info|warning|error|debug)\(\s*"Scraper \| (.+?)"\s*\)'
# Switches
RUN_EP_BOT: bool = guru_conf.get("run_ep_bot")
RUN_SUB_BOT: bool = guru_conf.get("run_sub_bot")
RUN_BACKUP_BOT: bool = guru_conf.get("run_backup_bot")

USE_PERSONAL_ACCOUNT: bool = guru_conf.get("use_personal")
WRITE_EP_TO_SUBREDDIT: bool = guru_conf.get("write_ep_to_subreddit")
UPDATE_WIKI: bool = guru_conf.get("update_wiki")
DO_FLAIR: bool = guru_conf.get("do_flair")
SKIP_OLD_THREADS: bool = guru_conf.get("skip_old_threads")
DEBUG: bool = guru_conf.get("debug")
INITIALIZE: bool = guru_conf.get("initialize")
MAX_EPISODE_IMPORT: int = int(guru_conf.get("max_import", 0))

# consts
BACKUP_SLEEP: int = guru_conf.get("backup_sleep")
EPISODE_MONITOR_SLEEP: int = guru_conf.get("episode_monitor_sleep")
MAX_SCRAPED_DUPES: int = guru_conf.get("max_scraped_dupes")

# links
MAIN_URL: str = guru_conf.get("main_url")
USER_AGENT: str = guru_conf.get("user_agent")
REDIRECT: str = guru_conf.get("redirect")

# paths
GURU_DB = DATA_DIR / guru_conf.get("db_name")
BACKUP_DIR = DATA_DIR / guru_conf.get("backup_dir")
BACKUP_JSON = BACKUP_DIR / guru_conf.get("backup_json")
BACKUP_JSON.touch(exist_ok=True)

# BACKUP_JSON = PROJECT_ROOT / guru_conf.get("back_js")


params_to_log_names = [
    "USE_PERSONAL_ACCOUNT",
    "WRITE_EP_TO_SUBREDDIT",
    "UPDATE_WIKI",
    "DO_FLAIR",
    "RUN_EP_BOT",
    "RUN_SUB_BOT",
    "RUN_BACKUP_BOT",
    "SKIP_OLD_THREADS",
    "DEBUG",
    "INITIALIZE",
]

# Create a list of tuples, each containing a parameter name and its value
params_to_log = [(param, globals()[param]) for param in params_to_log_names]


# Pass the list to your logger
def param_log_strs() -> list[str]:
    res = [f"{param}: {value}" for param, value in params_to_log if value]
    return res


PAGE_SIZE = 20
