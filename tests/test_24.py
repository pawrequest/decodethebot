import shelve

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from DecodeTheBot.dtb_htmx.episode_route import all_eps
from DecodeTheBot.dtg_bot import DTG
from DecodeTheBot.guru_config import GuruConfig, RedditConfig
from DecodeTheBot.models.episode_m import Episode
from DecodeTheBot.models.guru_m import Guru
from DecodeTheBot.models.reddit_m import RedditThread
from tests.conftest import test_session

app = FastAPI()
client = TestClient(app)


def test_config():
    gset = GuruConfig()
    rset = RedditConfig()
    assert gset
    assert rset


@pytest.fixture
async def dtg_bot():
    async with DTG() as dtg_:
        yield dtg_


@pytest.mark.asyncio
async def test_smth(dtg_bot):
    async with DTG() as dtgb:
        await dtgb.run()
        ...


@pytest.fixture
def session_populated(guru_settings, test_session):
    with shelve.open(guru_settings.backup_shelf) as shelf:
        episodes = shelf.get('episode')
        gurus = shelf.get('guru')
        reddits = shelf.get('reddit_thread')
    eps = [Episode.model_validate(ep, from_attributes=True) for ep in episodes]
    gurs = [Guru.model_validate(guru, from_attributes=True) for guru in gurus]
    reds = [RedditThread.model_validate(reddit, from_attributes=True) for reddit in reddits]
    test_session.add_all(eps)
    test_session.add_all(gurs)
    test_session.add_all(reds)
    test_session.commit()

    assert test_session.get(Episode, 1)
    assert test_session.get(Guru, 1)
    assert test_session.get(RedditThread, 1)

    yield test_session


def get_session():
    gset = GuruConfig()
    sesh = session_populated(guru_settings=gset, test_session=test_session())


@app.get('/')
async def read_main(request: Request):
    return all_eps(request=request, session=session_populated)


def test_read_main():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'msg': 'Hello World'}
