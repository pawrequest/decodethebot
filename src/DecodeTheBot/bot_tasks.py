import asyncio

import dotenv
from aiohttp import ClientSession
from asyncpraw import Reddit
from episode_scraper.episode_bot import EpisodeBot  # Episode, EpisodeBse
from loguru import logger
from redditbot import SubredditMonitor
from pawsupport import param_or_env
from sqlmodel import Session

dotenv.load_dotenv()




async def bot_tasks(session: Session, aio_session: ClientSession, reddit: Reddit):
    tasks = []
    bots = []
    bots.append(await ep_bot_(aio_session, session, tasks))

    try:
        back_bot = BackupBot(
            session=session,
            json_name_to_model_map=JSON_NAMES_TO_MODEL_MAP,
            backup_target=BACKUP_JSON,
        )
        pruner = Pruner(backup_target=BACKUP_JSON)
        back_bot.restore()
        tasks.append(asyncio.create_task(backup_tasks(back_bot, pruner)))
    except Exception as e:
        logger.error(f"Error initiating backup_bot: {e}")

    try:
        sub_bot = SubredditMonitor(session, Guru, subreddit)
        await sub_bot.run()
        tasks.append(asyncio.create_task(sub_bot.monitor()))
    except Exception as e:
        logger.error(f"Error initiating SubredditMonitor: {e}")

    return tasks


async def ep_bot_(session, aio_session, main_url=None):
    main_url = param_or_env("MAIN_URL", main_url)
    try:
        return await EpisodeBot.from_url(session, aio_session, main_url)
    except Exception as e:
        logger.error(f"Error initiating EpisodeBot: {e}")


