import asyncio

from dotenv import load_dotenv
from episode_scraper.episode_bot import EpisodeBot
from pawsupport import Pruner, SQLModelBot
from redditbot import SubredditMonitor
from sqlmodel import SQLModel, Session, select

from .core.consts import GURU_NAMES_FILE, PODCAST_URL, \
    logger
from .models.episode_ext import Episode
from .models.guru import Guru
from .models.reddit_ext import RedditThread as RedditThread
from .ui.mixin import title_or_name

load_dotenv()


async def restore_with_gurus(backup_bot, session):
    gurus_from_file(session, GURU_NAMES_FILE)
    backup_bot.restore()


async def monitor_tasks(session, subreddit):
    tasks = []
    thread_q = asyncio.Queue()
    monitor_bot = SubredditMonitor(subreddit=subreddit,
                                   session=session,
                                   # match_model=Guru,
                                   thread_db_type=RedditThread,
                                   )
    tasks.append(asyncio.create_task(monitor_bot.run_q2(thread_q)))
    tasks.append(asyncio.create_task(process_general(thread_q, session)))
    # tasks.append(asyncio.create_task(process_threads(session, thread_q)))
    return tasks


async def scraper_tasks(aio_session, session) -> list[asyncio.Task]:
    tasks = []
    episode_q = asyncio.Queue()
    ep_bot = await EpisodeBot.from_url(PODCAST_URL, session, aio_session,
                                       episode_db_type=Episode)
    tasks.append(asyncio.create_task(ep_bot.run_q(episode_q)))
    tasks.append(asyncio.create_task(process_general(episode_q, session)))
    # tasks.append(asyncio.create_task(process_episodes(episode_q, session)))
    return tasks


# async def process_episodes(queue: asyncio.Queue, session: Session):
#     while True:
#         episode = await queue.get()
#         guru_matches = await guru_matches_(session, episode)
#
#         if guru_matches:
#             for match in guru_matches:
#                 match.episodes.append(episode)
#             session.add(episode)
#             session.commit()
#         queue.task_done()


async def process_general(queue: asyncio.Queue, session: Session):
    while True:
        instance = await queue.get()
        guru_matches = await name_or_title_matches_(session, instance, Guru)
        episode_matches = await name_or_title_matches_(session, instance, Episode)
        thread_matches = await name_or_title_matches_(session, instance, RedditThread)

        if not any([guru_matches, episode_matches, thread_matches]):
            logger.debug(f"No matches for {title_or_name(instance)}")
            continue

        if guru_matches:
            instance.gurus.extend(guru_matches)

        if episode_matches:
            instance.episodes.extend(episode_matches)

        if thread_matches:
            instance.reddit_threads.extend(thread_matches)

        session.add(instance)
        session.commit()
        queue.task_done()


# async def process_threads(session, queue: asyncio.Queue):
#     while True:
#         submission = await queue.get()
#         # guru_matches = await guru_matches_(session, submission)
#         # episode_matches = await episode_matches_(session, submission)
#
#         guru_matches = await name_or_title_matches_(session, submission, Guru)
#         episode_matches = await name_or_title_matches_(session, submission, Episode)
#
#         if guru_matches or episode_matches:
#             try:
#                 thread = RedditThread.from_submission(submission)
#             except Exception as e:
#                 logger.error(f"Error creating thread from submission: {e}")
#                 continue
#
#             for match in guru_matches:
#                 try:
#                     match.reddit_threads.append(thread)
#                     session.add(thread)
#                 except Exception as e:
#                     logger.error(f"Error appending thread to match: {e}")
#                     continue
#             for match in episode_matches:
#                 try:
#                     match.reddit_threads.append(thread)
#                     session.add(thread)
#                 except Exception as e:
#                     logger.error(f"Error appending thread to match: {e}")
#                     continue
#             session.commit()
#         queue.task_done()


async def backup_and_prune(backupbot: SQLModelBot, pruner: Pruner, backup_sleep):
    while True:
        await asyncio.sleep(backup_sleep)
        await backupbot.backup()
        pruner.copy_and_prune()


# async def guru_matches_(session: Session, obj_with_title) -> list[SQLModel]:
#     gurus = session.exec(select(Guru)).all()
#     matched_tag_models = [_ for _ in gurus if await name_in_title(_, obj_with_title)]
#     if matched_tag_models:
#         logger.info(f"Found {len(matched_tag_models)} matches for {obj_with_title.title}")
#     return matched_tag_models


# async def name_matches_(session: Session, obj_with_title, match_model) -> list[SQLModel]:
#     all_insts = session.exec(select(match_model)).all()
#     matched_tag_models = [_ for _ in all_insts if await name_in_title(_, obj_with_title)]
#     if matched_tag_models:
#         logger.info(f"Found {len(matched_tag_models)} matches for {obj_with_title.title}")
#     return matched_tag_models


async def name_or_title_matches_(session: Session, obj_with_title_or_name, match_model) -> list[
    SQLModel]:
    db_objs = session.exec(select(match_model)).all()
    identifier = title_or_name(obj_with_title_or_name)
    if hasattr(match_model, 'title'):
        matched_tag_models = [_ for _ in db_objs if _.title.lower() in identifier.lower()]
    elif hasattr(match_model, 'name'):
        matched_tag_models = [_ for _ in db_objs if _.name.lower() in identifier.lower()]
    else:
        matched_tag_models = []
    if matched_tag_models:
        logger.info(f"Found {len(matched_tag_models)} matches for {obj_with_title_or_name.__class__.__name__} - {identifier}")
    return matched_tag_models


# async def episode_matches_(session: Session, obj_with_title) -> list[SQLModel]:
#     episodes = session.exec(select(Episode)).all()
#     matched_tag_models = [_ for _ in episodes if await title_in_title(_, obj_with_title)]
#     if matched_tag_models:
#         logger.info(f"Found {len(matched_tag_models)} matches for {obj_with_title.title}")
#     return matched_tag_models


# async def title_matches_(session: Session, obj_with_title, match_model) -> list[SQLModel]:
#     all_insts = session.exec(select(match_model)).all()
#     matched_tag_models = [_ for _ in all_insts if await title_in_title(_, obj_with_title)]
#     if matched_tag_models:
#         logger.info(f"Found {len(matched_tag_models)} matches for {obj_with_title.title}")
#     return matched_tag_models


# async def name_in_title(model_inst_with_name, obj_with_title):
#     return model_inst_with_name.name.lower() in obj_with_title.title.lower()
#
#
# async def title_in_title(model_inst_with_title, obj_with_title):
#     return model_inst_with_title.title.lower() in obj_with_title.title.lower()
#

def gurus_from_file(session, infile):
    with open(infile, 'r') as f:
        guru_names = f.read().split(',')
    session_gurus = session.exec(select(Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f"Adding {len(new_gurus)} new gurus")
        gurus = [Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()
