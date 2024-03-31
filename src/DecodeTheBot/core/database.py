import os
import pathlib

from sqlalchemy import create_engine, text
from sqlmodel import SQLModel, Session

from DecodeTheBot.core.consts import logger


def get_db_url():
    DB_LOC = os.environ.get('GURU_DB')
    logger.info(f"USING DB FILE: {DB_LOC}")
    DB_PATH = pathlib.Path(DB_LOC)
    DBLITE = f'sqlite:///{DB_PATH}' if DB_PATH.is_file() else 'sqlite:///guru.db'
    return DBLITE


def engine_():
    db_url = get_db_url()
    connect_args = {"check_same_thread": False}

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
