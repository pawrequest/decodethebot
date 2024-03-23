# no dont do this!! from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from asyncpraw.models import Submission
from fastui import components as c
from suppawt import get_set
import pydantic as _p
import sqlalchemy as sqa
import sqlmodel as sqm

from DecodeTheBot.models.links import RedditThreadEpisodeLink, RedditThreadGuruLink

if TYPE_CHECKING:
    from DecodeTheBot.models.episodedb import Episode
    from DecodeTheBot.models.guru import Guru


def submission_to_dict(submission: Submission):
    serializable_types = (int, float, str, bool, type(None))
    if isinstance(submission, Submission):
        submission = vars(submission)
    return {k: v for k, v in submission.items() if isinstance(v, serializable_types)}


class RedditThreadBase(sqm.SQLModel):
    reddit_id: str = sqm.Field(index=True, unique=True)
    title: str
    shortlink: str
    created_datetime: datetime
    submission: Dict = sqm.Field(default=None, sa_column=sqa.Column(sqa.JSON))

    @_p.field_validator("submission", mode="before")
    def validate_submission(cls, v):
        return submission_to_dict(v)

    @classmethod
    def from_submission(cls, submission: Submission):
        tdict = dict(
            reddit_id=submission.id,
            title=submission.title,
            shortlink=submission.shortlink,
            created_datetime=submission.created_utc,
            submission=submission,
        )
        return cls.model_validate(tdict)


class RedditThread(RedditThreadBase, table=True, extend_existing=True):
    id: Optional[int] = sqm.Field(default=None, primary_key=True)

    gurus: List["Guru"] = sqm.Relationship(
        back_populates="reddit_threads", link_model=RedditThreadGuruLink
    )
    episodes: List["Episode"] = sqm.Relationship(
        back_populates="reddit_threads", link_model=RedditThreadEpisodeLink
    )

    @property
    def get_hash(self):
        return get_set.hash_simple_md5([self.reddit_id])

    @property
    def slug(self):
        return f"/red/{self.id}"

    def ui_detail(self):
        return c.Details(data=self)

    @classmethod
    def rout_prefix(cls):
        return "/red/"
