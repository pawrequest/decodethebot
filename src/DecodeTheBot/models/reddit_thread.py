# no dont do this!! from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from asyncpraw.models import Submission
from fastui.components import Details
from pawsupport.fastui_ps.fastui_support import Flex
from pawsupport.misc_ps import hash_simple_md5
from pydantic import field_validator
from sqlalchemy import Column
from sqlmodel import Field, JSON, Relationship, SQLModel

from DecodeTheBot.models.links import RedditThreadEpisodeLink, RedditThreadGuruLink

if TYPE_CHECKING:
    from DecodeTheBot.models.episode import Episode
    from DecodeTheBot.models.guru import Guru


def submission_to_dict(submission: Submission):
    serializable_types = (int, float, str, bool, type(None))
    if isinstance(submission, Submission):
        submission = vars(submission)
    return {k: v for k, v in submission.items() if isinstance(v, serializable_types)}

 
class RedditThreadBase(SQLModel):
    reddit_id: str = Field(index=True, unique=True)
    title: str
    shortlink: str
    created_datetime: datetime
    submission: Dict = Field(default=None, sa_column=Column(JSON))

    @field_validator("submission", mode="before")
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
    id: Optional[int] = Field(default=None, primary_key=True)

    gurus: List["Guru"] = Relationship(
        back_populates="reddit_threads", link_model=RedditThreadGuruLink
    )
    episodes: List["Episode"] = Relationship(
        back_populates="reddit_threads", link_model=RedditThreadEpisodeLink
    )

    @property
    def get_hash(self):
        return hash_simple_md5([self.reddit_id])

    @property
    def slug(self):
        return f"/red/{self.id}"

    def ui_detail(self) -> Flex:
        return Details(data=self)

    @classmethod
    def rout_prefix(cls):
        return "/red/"