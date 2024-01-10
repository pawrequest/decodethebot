import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from episode_bot import EpisodeBot
from episode_model import Episode

@pytest.fixture(scope="session")
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


MAIN_URL = "https://decoding-the-gurus.captivate.fm"


@pytest_asyncio.fixture
async def episode_bot(session):
    return await EpisodeBot.from_url(MAIN_URL, session)


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
