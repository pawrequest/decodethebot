from asyncio import Queue

from pawsupport import async_support as psa, sqlmodel_support as psql
from sqlalchemy import create_engine, text
from sqlmodel import SQLModel, Session, select

from .consts import logger, INIT_EPS
from ..models.episode import Episode
from ..models.guru import Guru
from ..models.reddit_thread import RedditThread


def engine_(config=None):
    config = config or engine_config()
    db_url = config["db_url"]
    connect_args = config["connect_args"]

    return create_engine(db_url, echo=False, connect_args=connect_args)


def engine_config():
    return {"db_url": "sqlite:///guru.db", "connect_args": {"check_same_thread": False}}


def get_session(engine=None) -> Session:
    if engine is None:
        engine = engine_()
    with Session(engine) as session:
        yield session
    session.close()


def create_db(engine=None):
    if engine is None:
        engine = engine_()
    SQLModel.metadata.create_all(engine)


def trim_db(session):
    ep_trim = 108
    red_trim = 20
    stmts = [
        text(_)
        for _ in [
            f"delete from episode where id >={ep_trim}",
            f"delete from guruepisodelink where episode_id >={ep_trim}",
            f"delete from redditthreadepisodelink where episode_id >={ep_trim}",
            f"delete from redditthread where id >={red_trim}",
            f"delete from redditthreadepisodelink where reddit_thread_id >={red_trim}",
            f"delete from redditthreadgurulink where reddit_thread_id >={red_trim}",
        ]
    ]
    try:
        [session.execute(_) for _ in stmts]
        session.commit()
    except Exception as e:
        logger.error(e)


@psa.quiet_cancel_try_log_as
async def init_eps(session, queue: Queue):
    ep_i = 0
    max_eps = INIT_EPS
    logger.info("Initialising episodes")
    eps = []
    ep = await queue.get()
    ep = Episode.model_validate(ep)
    eps.append(ep)
    ep_i += 1
    if ep_i >= max_eps:
        return

    eps = sorted(eps, key=lambda _: _.date)
    for ep in eps:
        if psql.obj_in_session(session, ep, Episode):
            continue
        logger.info(f"Adding {ep.title}")
        session.add(ep)
        thread_matches = psql.db_obj_matches(session, ep, RedditThread)
        guru_matches = psql.db_obj_matches(session, ep, Guru)
        psql.assign_rel(ep, RedditThread, thread_matches)
        psql.assign_rel(ep, Guru, guru_matches)
    if session.new:
        session.commit()


def gurus_from_file(session, infile):
    with open(infile, "r") as f:
        guru_names = f.read().split(",")
    session_gurus = session.exec(select(Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f"Adding {len(new_gurus)} new gurus")
        gurus = [Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()
