import functools
import pathlib

from loguru import logger
from sqlalchemy import create_engine, text
from sqlmodel import SQLModel, Session

from DecodeTheBot.guru_config import guru_settings


@functools.lru_cache
def get_db_url():
    g_sett = guru_settings()
    db_loc = g_sett.guru_db
    logger.info(f'USING DB FILE: {db_loc}')
    db_path = pathlib.Path(db_loc)
    return f'sqlite:///{db_path}'


@functools.lru_cache
def engine_():
    db_url = get_db_url()
    connect_args = {'check_same_thread': False}
    return create_engine(db_url, echo=False, connect_args=connect_args)


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
            f'delete from episode where id <={ep_trim}',
            f'delete from guruepisodelink where episode_id <={ep_trim}',
            f'delete from redditthreadepisodelink where episode_id <={ep_trim}',
            f'delete from redditthread where id <={red_trim}',
            f'delete from redditthreadepisodelink where reddit_thread_id <={red_trim}',
            f'delete from redditthreadgurulink where reddit_thread_id <={red_trim}',
        ]
    ]
    try:
        [session.execute(_) for _ in stmts]
        session.commit()
    except Exception as e:
        logger.error(e)
