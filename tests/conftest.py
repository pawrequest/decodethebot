# from __future__ import annotations
#
# import json
# from random import randint
#
# import pytest
# from asyncpraw import Reddit
import inspect
import json
import re
from random import randint

import pytest
from loguru import logger as _logger

# from sqlalchemy import create_engine
# from sqlalchemy.pool import StaticPool
# from sqlmodel import Session
# from starlette.testclient import TestClient
#
# from data.consts import EPISODES_MOD
# from gurupod.core.database import SQLModel, get_session
# from gurupod.core.gurulog import get_logger
# from gurupod.models.episode import Episode, EpisodeBase
# from gurupod.models.responses import EpisodeResponseNoDB
# from gurupod.reddit_monitor.managers import reddit_cm
# from main import app
#
from asyncpraw import Reddit
from suppawt.pawlogger.config_loguru import get_loguru
from sqlalchemy import StaticPool, create_engine
from sqlmodel import SQLModel, Session
from src.DecodeTheBot.models.guru import Guru  # noqa F401
from src.DecodeTheBot.models.reddit_ext import RedditThread  # noqa F401

from DecodeTheBot.models.episode_m import Episode
from src.DecodeTheBot.dtg_bot import gurus_from_file
from src.DecodeTheBot.core.consts import BACKUP_JSON, GURU_NAMES_FILE


@pytest.fixture(scope='session')
def test_session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(scope='session')
def test_session_with_gurus(test_session):
    gurus_from_file(test_session, GURU_NAMES_FILE)
    yield test_session


MAIN_URL = 'https://decoding-the-gurus.captivate.fm'

TEST_DB = 'sqlite://'
ENGINE = create_engine(
    TEST_DB,
    connect_args={'check_same_thread': False},
    poolclass=StaticPool,
)


async def override_subreddit():
    try:
        reddit = Reddit()
        subreddit = await reddit.subreddit('test')
        yield subreddit
    finally:
        await reddit.close()


def override_session():
    try:
        session = Session(ENGINE)
        yield session
    finally:
        session.close()


#
#
def override_logger():
    logger = _logger
    logger.remove()
    return logger


#

# client = TestClient(app)
#
# app.dependency_overrides[get_logger] = override_logger
# app.dependency_overrides[get_session] = override_session
# app.dependency_overrides[reddit_cm()] = override_subreddit


#
# @pytest.fixture(scope="function")
def test_logger(tmp_path):
    logger = get_loguru('local')
    logger.remove()
    test_loc = tmp_path / 'test.log'
    logger.add(test_loc)
    logger.info('test')
    logged_line = inspect.getframeinfo(inspect.currentframe()).lineno - 1
    with open(test_loc) as f:
        LOG1 = f.readline()
    pat_xml = r'^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d{3}\s)\|(\s[A-Z]*\s*)\|(\s.+:.+:\d+\s-\s.*)$'
    match = re.match(pat_xml, LOG1)

    assert match
    assert match.string.endswith(f' | INFO     | DecodeTheBot.tests.conftest:test_logger:{logged_line} - test\n')

    # yield logger


#
#
# @pytest.mark.asyncio
# @pytest.fixture(scope="session")
# async def cached_scrape():
#     response = client.get("/eps/scrape?max_rtn=5")
#     assert response.status_code == 200
#     res = EpisodeResponseNoDB.model_validate(response.json())
#     return res
#
#
@pytest.fixture(scope='session')
def all_episodes_json():
    with open(BACKUP_JSON) as f:
        res = json.load(f)['episode']
        return [json.loads(_) for _ in res]


#
@pytest.fixture(scope='function')
def random_episode(all_episodes_json):
    res = all_episodes_json[randint(0, len(all_episodes_json) - 1)]
    return Episode.model_validate(res)


@pytest.mark.asyncio
async def test_ep_json(random_episode):
    assert isinstance(random_episode, Episode)


# @pytest.fixture(scope="function")
# def random_episode_validated(random_episode_json) -> EpisodeBase:
#     return EpisodeBase.model_validate(random_episode_json)
#
#
# @pytest.fixture(scope="function")
# def episodes_weird(all_episodes_json):
#     names = [
#         "Interview with Josh Szeps, The Rumble from Downunder",
#         "Interview with the Conspirituality Trio: Navigating the Chakras of Conspiracy",
#     ]
#     weird = [_ for _ in all_episodes_json if _["title"] in names]
#     return [EpisodeBase.model_validate(_) for _ in weird]
#
#
@pytest.fixture(scope='session')
def test_db():
    SQLModel.metadata.create_all(ENGINE)

    # EpisodeBase.metadata.create_all(bind=ENGINE)
    # Episode.metadata.create_all(bind=ENGINE)
    yield
    SQLModel.metadata.drop_all(bind=ENGINE)
    # Episode.metadata.drop_all(bind=ENGINE)


#
#
@pytest.fixture(scope='function')
def blank_test_db(test_db):
    Episode.metadata.drop_all(bind=ENGINE)
    Episode.metadata.drop_all(bind=ENGINE)
    Episode.metadata.create_all(bind=ENGINE)
    Episode.metadata.create_all(bind=ENGINE)
    yield


#
#
@pytest.fixture(scope='module')
def markup_sample():
    return """# Interview with Daniël Lakens and Smriti Mehta on the state of Psychology

[play on captivate.fm](https://decoding-the-gurus.captivate.fm/episode/interview-with-daniel-lakens-and-smriti-mehta-on-the-state-of-psychology)
### Published Saturday November 18 2023

### Show Notes

We are back with more geeky academic discussion than you can shake a stick at. This week we are doing our bit to save civilization by discussing issues in contemporary science, the replication crisis, and open science reforms with fellow psychologists/meta-scientists/podcasters, Daniël Lakens and Smriti Mehta. Both Daniël and Smriti are well known for their advocacy for methodological reform and have been hosting a (relatively) new podcast, Nullius in Verba, all about 'science—what it is and what it could be'.

We discuss a range of topics including questionable research practices, the implications of the replication crisis, responsible heterodoxy, and the role of different communication modes in shaping discourses.

Also featuring: exciting AI chat, Lex and Elon being teenage edge lords, feedback on the Huberman episode, and as always updates on Matt's succulents.

Back soon with a Decoding episode!

### Show Links

[Nullius in Verba Podcast](https://nulliusinverba.podbean.com/)

[Lee Jussim's Timeline on the Klaus Fiedler Controversy](https://unsafescience.substack.com/p/notes-from-a-witch-hunt)

[a list of articles/sources covering the topic](https://unsafescience.substack.com/p/pops-fiasco-orientation-page)

[Elon Musk: War, AI, Aliens, Politics, Physics, Video Games, and Humanity | Lex Fridman Podcast #400](https://www.youtube.com/watch?v=JN3KPFbWCy8)

[Daniel's MOOC on Improving Your Statistical Inference](https://www.coursera.org/learn/statistical-inferences?utm_source=gg&utm_medium=sem&utm_campaign=B2C_APAC__branded_FTCOF_courseraplus_arte_PMax_set3&utm_content=Degree&campaignid=20520161513&adgroupid=&device=c&keyword=&matchtype=&network=x&devicemodel=&adpostion=&creativeid=&hide_mobile_promo&gclid=CjwKCAiAu9yqBhBmEiwAHTx5p5fBUeqyPyuUdxMHD5O0RbTWsScGjvzrsdeuIS3FfEHVuYVnX5PxphoC6DMQAvD_BwE)

[Critical commentary on Fiedler controversy at Replicability-Index](https://replicationindex.com/2022/12/30/klaus-fiedler-is-a-victim-of-his-own-arrogance/)



 ---"""
