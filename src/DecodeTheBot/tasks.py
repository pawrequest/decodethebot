import asyncio
from typing import TypeVar, Union

from asyncpraw.models import Submission, Subreddit
from dotenv import load_dotenv
from episode_scraper.soups import MainSoup
from pawsupport import Pruner, SQLModelBot
from sqlmodel import Session, select

from .core.consts import GURU_NAMES_FILE, PODCAST_URL, SCRAPER_SLEEP, logger
from .models.episode_ext import Episode
from .models.guru import Guru
from .models.reddit_ext import RedditThread as RedditThread
from .ui.mixin import title_or_name

load_dotenv()

DB_MODEL_TYPE = TypeVar("DB_MODEL_TYPE", bound=Union[Guru, Episode, RedditThread])


async def restore_with_gurus(backup_bot, session):
    gurus_from_file(session, GURU_NAMES_FILE)
    backup_bot.restore()


async def q_eps(aio_session, process_q):
    while True:
        main_soup = await MainSoup.from_url(PODCAST_URL, aio_session)
        async for episode in main_soup.episode_stream(aio_session):
            logger.info(f"Episode: {episode.title}")
            episode = Episode.model_validate(episode)
            await process_q.put(episode)
        await asyncio.sleep(SCRAPER_SLEEP)


async def q_threads(session, subreddit: Subreddit, process_q):
    sub_stream = subreddit.stream.submissions(skip_existing=False)
    async for sub in sub_stream:
        if submission_exists(session, sub):
            continue
        thread = RedditThread.from_submission(sub)

        logger.info(f"Thread: {thread.title}")
        await process_q.put(thread)


async def process_queue(queue: asyncio.Queue, session: Session):
    while True:
        instance = await queue.get()
        guru_matches = name_or_title_matches_(session, instance, Guru)
        episode_matches = name_or_title_matches_(session, instance, Episode)
        thread_matches = name_or_title_matches_(session, instance, RedditThread)

        if not any([guru_matches, episode_matches, thread_matches]):
            continue
        if guru_matches and not isinstance(instance, Guru):
            instance.gurus.extend(guru_matches)

        if episode_matches and not isinstance(instance, Episode):
            instance.episodes.extend(episode_matches)

        if thread_matches and not isinstance(instance, RedditThread):
            instance.reddit_threads.extend(thread_matches)

        session.add(instance)
        session.commit()
        queue.task_done()


async def backup_and_prune(backupbot: SQLModelBot, pruner: Pruner, backup_sleep):
    while True:
        await asyncio.sleep(backup_sleep)
        await backupbot.backup()
        pruner.copy_and_prune()


# async def name_or_title_matches_old(session: Session, obj_with_title_or_name, match_model) -> list[
#     SQLModel]:
#     db_objs = session.exec(select(match_model)).all()
#     identifier = title_or_name(obj_with_title_or_name)
#     if hasattr(match_model, 'title'):
#         matched_tag_models = [_ for _ in db_objs if _.title.lower() in identifier.lower()]
#     elif hasattr(match_model, 'name'):
#         matched_tag_models = [_ for _ in db_objs if _.name.lower() in identifier.lower()]
#     else:
#         matched_tag_models = []
#     if matched_tag_models:
#         logger.info(
#             f"Found {len(matched_tag_models)} {match_model.__class__._name__} matches for {obj_with_title_or_name.__class__.__name__} - {identifier}")
#     return matched_tag_models


def name_or_title_matches_(
    session: Session, obj_with_title_or_name: DB_MODEL_TYPE, match_model: type(DB_MODEL_TYPE)
) -> list[DB_MODEL_TYPE]:
    db_objs = session.exec(select(match_model)).all()
    identifier = title_or_name(obj_with_title_or_name)
    if hasattr(match_model, "title"):
        matched_tag_models = [_ for _ in db_objs if _.title.lower() in identifier.lower()]
    elif hasattr(match_model, "name"):
        matched_tag_models = [_ for _ in db_objs if _.name.lower() in identifier.lower()]
    else:
        matched_tag_models = []
    if matched_tag_models:
        logger.debug(
            f"Found {len(matched_tag_models)} {match_model.__name__} matches for {obj_with_title_or_name.__class__.__name__} - {identifier}"
        )
    return matched_tag_models


def gurus_from_file(session, infile):
    with open(infile, "r") as f:
        guru_names = f.read().split(",")
    session_gurus = session.exec(select(Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f"Adding {len(new_gurus)} new gurus")
        gurus = [Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()


def submission_exists(session, submission: Submission) -> bool:
    """Checks if a Submission ID is already in the database of RedditThreads"""
    existing_thread = session.exec(
        select(RedditThread).where((RedditThread.reddit_id == submission.id))
    ).first()
    return existing_thread is not None
