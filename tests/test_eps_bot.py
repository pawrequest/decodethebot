# from __future__ import annotations

import pytest
import pytest_asyncio
from episode_scraper.episode_bot import EpisodeBot
from sqlmodel import select

from src.DecodeTheBot.models.episode import Episode
from src.DecodeTheBot.models.guru import Guru
from src.DecodeTheBot.models.reddit_ext import RedditThread
from tests.conftest import MAIN_URL

spurious_import = Guru  # protect from ruff
another_ = RedditThread  # protect from ruff


@pytest_asyncio.fixture
async def episode_bot(test_session):
    ep_bot: EpisodeBot = await EpisodeBot.from_url(MAIN_URL, test_session, episode_db_type=Episode)
    return ep_bot


@pytest.mark.asyncio
async def test_episode_bot_initialization(episode_bot):
    assert isinstance(episode_bot, EpisodeBot)


@pytest.mark.asyncio
async def test_gets_episodes_and_skip_existing(episode_bot, test_session):
    e1 = await anext(episode_bot.run())
    eps = test_session.exec(select(Episode)).all()
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
