import dotenv
import pytest_asyncio
from sqlmodel import SQLModel, Session, create_engine
import pytest
from asyncpraw.reddit import Subreddit

from redditbot.monitor import SubredditMonitor, submission_to_thread
from redditbot.managers import subreddit_cm

from src.DecodeTheBot.models.reddit_ext import RedditThread
from src.DecodeTheBot.models.guru import Guru
from src.DecodeTheBot.models.episode_ext import Episode

dotenv.load_dotenv()


spurious_import = Guru  # protect from ruff
spurious_import2 = Episode  # protect from ruff

@pytest.fixture(scope="function")
def test_engine(tmp_path):
    # Create a test engine, possibly using an in-memory database
    return create_engine(f"sqlite:///{tmp_path}/test.db")


@pytest.fixture(scope="function")
def test_session(test_engine):
    # Create a session for the test database
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session


@pytest.mark.asyncio
async def test_r():
    async with subreddit_cm() as subreddit:
        assert isinstance(subreddit, Subreddit)


@pytest_asyncio.fixture
async def monitor_bot(test_session):
    async with subreddit_cm() as subreddit:
        mon = SubredditMonitor(session=test_session, match_model=Guru, subreddit=subreddit, thread_db_type=RedditThread)
        yield mon


@pytest.mark.asyncio
async def test_montior_bot(monitor_bot):
    assert isinstance(monitor_bot, SubredditMonitor)


@pytest.mark.asyncio
async def test_monitor(test_session):
    test_session.add(Guru(name="Joe Rogan"))
    test_session.commit()

    async with subreddit_cm("test") as subreddit:
        mon = SubredditMonitor(session=test_session, match_model=Guru, subreddit=subreddit, thread_db_type=RedditThread)
        sub_stream = mon.subreddit.stream.submissions(skip_existing=False)
        async for sub in mon.filter_existing_submissions(sub_stream):
            if matches := await mon.get_matches(sub):
                thread = await submission_to_thread(sub)
                assert isinstance(thread, RedditThread)
                for match in matches:
                    assert isinstance(match, Guru)
                    tds = match.reddit_threads
                    match.reddit_threads.append(thread)
                test_session.add(thread)
                test_session.commit()
                test_session.refresh(thread)
                assert thread.gurus
                return


def test_get_matches(subreddit_monitor):
    # Test the get_matches method
    # Provide a submission and check if it correctly identifies matching tags
    pass


def test_database_operations(subreddit_monitor):
    # Test database operations
    # Check if the correct entries are made in the database for new submissions and matches
    pass
