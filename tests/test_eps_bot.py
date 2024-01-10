# from __future__ import annotations

import pytest
import pytest_asyncio
from episode_scraper.episode_bot import EpisodeBot
from sqlmodel import SQLModel, Session, create_engine, select

from src.decodethebot.models.episode_ext import Episode
from src.decodethebot.models.guru import Guru


@pytest.fixture(scope="session")
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


MAIN_URL = "https://decoding-the-gurus.captivate.fm"


@pytest_asyncio.fixture
async def episode_bot(session):
    ep_bot: EpisodeBot = await EpisodeBot.from_url(MAIN_URL, session, episode_db_type=Episode)
    return ep_bot


@pytest.mark.asyncio
async def test_episode_bot_initialization(episode_bot):
    assert isinstance(episode_bot, EpisodeBot)


@pytest.mark.asyncio
async def test_gets_episodes_and_skip_existing(episode_bot, session):
    e1 = await anext(episode_bot.run())
    eps = session.exec(select(Episode)).all()
    assert e1 in eps
    e2 = await anext(episode_bot.run())
    assert e2 != e1


# def test_ep_ext():
#     ep1 = EpisodeExt(
#         url="https://decoding-the-gurus.captivate.fm/episode/why-are-we-so-afraid-of-death",
#         title="Why are we so afraid of death?",
#         date="2021-06-03T00:00:00+00:00",
#         links={},
#         notes=[],
#
#     )
#     ep = EpisodeExt.model_validate(
#         ep1
#     )
#     assert isinstance(ep, EpisodeExt)
