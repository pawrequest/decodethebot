from __future__ import annotations

from contextlib import asynccontextmanager

from asyncpraw.reddit import Reddit, Subreddit

from DecodeTheBot.guru_config import RedditConfig, reddit_settings


@asynccontextmanager
async def reddit_cm(settings: RedditConfig | None = None) -> Reddit:
    sett = settings or reddit_settings()
    try:
        async with Reddit(
            client_id=sett.client_id,
            client_secret=sett.client_secret,
            user_agent=sett.user_agent,
            redirect_uri=sett.redirect_uri,
            refresh_token=sett.refresh_token,
        ) as reddit:
            yield reddit
    finally:
        await reddit.close()


@asynccontextmanager
async def subreddit_cm(settings: RedditConfig | None = None) -> Subreddit:
    sett = settings or reddit_settings()
    async with reddit_cm(settings) as reddit:
        subreddit: Subreddit = await reddit.subreddit(sett.subreddit_name)
        try:
            yield subreddit
        finally:
            await reddit.close()
