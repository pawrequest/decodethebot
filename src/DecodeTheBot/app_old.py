# import asyncio
# import sys
# from contextlib import asynccontextmanager
# from functools import lru_cache
#
# from aiohttp import ClientSession
# from dotenv import load_dotenv
# from episode_scraper.episode_bot import EpisodeBot
# from fastapi import FastAPI
# from fastui import prebuilt_html
# from fastui.dev import dev_fastapi_app
# from pawsupport import Pruner, SQLModelBot
# from redditbot import SubredditMonitor, subreddit_cm
# from sqlmodel import SQLModel, Session, select
# from fastapi.responses import HTMLResponse, PlainTextResponse
#
# from .core.consts import BACKUP_DIR, BACKUP_JSON, BACKUP_SLEEP, GURU_NAMES_FILE, PODCAST_URL, \
#     RESTORE_FROM_JSON, SUBREDDIT_NAME, logger
# from .core.database import create_db, engine_
# from .models.episode_ext import Episode
# from .models.guru import Guru
# from .models.reddit_ext import RedditThread as RedditThread
#
# load_dotenv()
#
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     tasks = []
#     try:
#         create_db()
#         logger.info("tables created", bot_name="BOOT")
#         with Session(engine_()) as session:
#
#             backup_bot = SQLModelBot(session, json_map_(), BACKUP_JSON, output_dir=BACKUP_DIR)
#             pruner = Pruner(backup_target=BACKUP_JSON, output_dir=BACKUP_DIR)
#
#             if RESTORE_FROM_JSON:
#                 await restore_with_gurus(backup_bot, session)
#             tasks.append(asyncio.create_task(backup_and_prune(backup_bot, pruner, BACKUP_SLEEP)))
#
#             async with ClientSession() as aio_session:
#                 tasks.extend(await scraper_tasks(aio_session, session))
#                 async with subreddit_cm(sub_name=SUBREDDIT_NAME) as subreddit:  # noqa E1120
#                     tasks.extend(await monitor_tasks(session, subreddit))
#
#                     yield
#                     logger.info('exit backup')
#
#                     await backup_bot.backup()
#
#     finally:
#         logger.info("Shutting down")
#         for task in tasks:
#             task.cancel()
#
#         await asyncio.gather(*tasks, return_exceptions=True)
#
#
# async def restore_with_gurus(backup_bot, session):
#     gurus_from_file(session, GURU_NAMES_FILE)
#     # todo: restore from json
#     # backup_bot.restore()
#
#
# async def monitor_tasks(session, subreddit):
#     tasks = []
#     thread_q = asyncio.Queue()
#     monitor_bot = SubredditMonitor(subreddit=subreddit,
#                                    session=session,
#                                    # match_model=Guru,
#                                    thread_db_type=RedditThread,
#                                    )
#     tasks.append(asyncio.create_task(monitor_bot.run_q2(thread_q)))
#     tasks.append(asyncio.create_task(process_threads(session, thread_q)))
#     return tasks
#
#
# async def scraper_tasks(aio_session, session) -> list[asyncio.Task]:
#     tasks = []
#     episode_q = asyncio.Queue()
#     ep_bot = await EpisodeBot.from_url(PODCAST_URL, session, aio_session,
#                                        episode_db_type=Episode)
#     tasks.append(asyncio.create_task(ep_bot.run_q(episode_q)))
#     tasks.append(asyncio.create_task(process_episodes(episode_q, session)))
#     return tasks
#
#
# frontend_reload = "--reload" in sys.argv
# if frontend_reload:
#     app = dev_fastapi_app(lifespan=lifespan)
# else:
#     app = FastAPI(lifespan=lifespan)
#
# from .routers.eps import router as eps_router
# from .routers.guroute import router as guru_router
# from .routers.main import router as main_router
# from .routers.red import router as red_router
# from .routers.forms import router as forms_router
#
# app.include_router(forms_router, prefix="/api/forms")
# app.include_router(eps_router, prefix="/api/eps")
# app.include_router(guru_router, prefix="/api/guru")
# app.include_router(red_router, prefix="/api/red")
#
# app.include_router(main_router, prefix="/api")
#
#
# @app.get("/robots.txt", response_class=PlainTextResponse)
# async def robots_txt() -> str:
#     return "User-agent: *\nAllow: /"
#
#
# @app.get("/favicon.ico", status_code=404, response_class=PlainTextResponse)
# async def favicon_ico() -> str:
#     return "page not found"
#
#
# @app.get("/{path:path}")
# async def html_landing() -> HTMLResponse:
#     return HTMLResponse(prebuilt_html(title="DecodeTheBot"))
#
#
# @lru_cache()
# def json_map_():
#     from .core.json_map import JSON_NAMES_TO_MODEL_MAP
#     return JSON_NAMES_TO_MODEL_MAP
#
#
# async def process_episodes(queue: asyncio.Queue, session: Session):
#     while True:
#         episode = await queue.get()
#         guru_matches = await guru_matches_(session, episode)
#
#
#         if guru_matches:
#             for match in guru_matches:
#                 match.episodes.append(episode)
#             session.add(episode)
#             session.commit()
#         queue.task_done()
#
#
# async def process_threads(session, queue: asyncio.Queue):
#     while True:
#         submission = await queue.get()
#         guru_matches = await guru_matches_(session, submission)
#         episode_matches = await episode_matches_(session, submission)
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
#
#
# async def backup_and_prune(backupbot: SQLModelBot, pruner: Pruner, backup_sleep):
#     while True:
#         await asyncio.sleep(backup_sleep)
#         await backupbot.backup()
#         pruner.copy_and_prune()
#
#
# async def guru_matches_(session: Session, obj_with_title) -> list[SQLModel]:
#     gurus = session.exec(select(Guru)).all()
#     matched_tag_models = [_ for _ in gurus if await name_in_title(_, obj_with_title)]
#     if matched_tag_models:
#         logger.info(f"Found {len(matched_tag_models)} matches for {obj_with_title.title}")
#     return matched_tag_models
#
#
# async def episode_matches_(session: Session, obj_with_title) -> list[SQLModel]:
#     episodes = session.exec(select(Episode)).all()
#     matched_tag_models = [_ for _ in episodes if await title_in_title(_, obj_with_title)]
#     if matched_tag_models:
#         logger.info(f"Found {len(matched_tag_models)} matches for {obj_with_title.title}")
#     return matched_tag_models
#
#
# async def title_matches_(session: Session, obj_with_title) -> list[SQLModel]:
#     all_insts = session.exec(select(type(obj_with_title))).all()
#     matched_tag_models = [_ for _ in all_insts if await title_in_title(_, obj_with_title)]
#     if matched_tag_models:
#         logger.info(f"Found {len(matched_tag_models)} matches for {obj_with_title.title}")
#     return matched_tag_models
#
#
# async def name_in_title(model_inst_with_name, obj_with_title):
#     return model_inst_with_name.name.lower() in obj_with_title.title.lower()
#
# async def title_in_title(model_inst_with_title, obj_with_title):
#     return model_inst_with_title.title.lower() in obj_with_title.title.lower()
#
#
# def gurus_from_file(session, infile):
#     with open(infile, 'r') as f:
#         guru_names = f.read().split(',')
#     session_gurus = session.exec(select(Guru.name)).all()
#     if new_gurus := set(guru_names) - set(session_gurus):
#         logger.info(f"Adding {len(new_gurus)} new gurus")
#         gurus = [Guru(name=_) for _ in new_gurus]
#         session.add_all(gurus)
#         session.commit()
