# no dont do this!! from __future__ import annotations
# it does this :(
"""sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[Guru(guru)]'. Original exception was: When initializing mapper Mapper[Guru(guru)], expression "relationship("List['Episode']")" seems to be using a generic class as the argument to relationship(); please state the generic argument using an annotation, e.g. "episodes: Mapped[List['Episode']] = relationship()"
E           sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[Guru(guru)], expression "relationship("List['Episode']")" seems to be using a generic class as the argument to relationship(); please state the generic argument using an annotation, e.g. "episodes: Mapped[List['Episode']] = relationship()"

"""
from functools import cached_property
from typing import ClassVar, TYPE_CHECKING

import sqlmodel
from pydantic import computed_field
from sqlmodel import Field, Relationship, SQLModel
import sqlalchemy as sa

from .links import GuruEpisodeLink, RedditThreadGuruLink

if TYPE_CHECKING:
    from .episode_m import Episode
    from .reddit_m import RedditThread


class GuruBase(SQLModel):
    name: str = Field(index=True, unique=True)
    notes: list[str] | None = Field(default_factory=list)


class Guru(GuruBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    notes: list[str] | None = Field(default_factory=list, sa_column=sqlmodel.Column(sa.JSON))

    episodes: list['Episode'] = Relationship(back_populates='gurus', link_model=GuruEpisodeLink)

    reddit_threads: list['RedditThread'] = Relationship(back_populates='gurus', link_model=RedditThreadGuruLink)

    rout_prefix: ClassVar[str] = 'guru'

    @cached_property
    def slug(self):
        return f'/{self.__class__.rout_prefix}/{self.id}'

    @computed_field
    def interest(self) -> int:
        return len(self.episodes) + len(self.reddit_threads)
