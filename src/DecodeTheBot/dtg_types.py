from dataclasses import dataclass
from typing import Sequence, TypeVar, Union

from sqlmodel import SQLModel
import pydantic as _p

from DecodeTheBot.models import episodedb, guru, links, reddit_thread, responses

DB_MODELS = (guru.Guru, episodedb.Episode, reddit_thread.RedditThread)
LINK_MODELS = (links.GuruEpisodeLink, links.RedditThreadEpisodeLink, links.RedditThreadGuruLink)
ALL_MODELS = (*DB_MODELS, *LINK_MODELS)
ALL_MODELS_TYPE = Union[ALL_MODELS]
DB_MODEL_TYPE = Union[DB_MODELS]
DB_MODEL_VAR = TypeVar("DB_MODEL_VAR", bound=DB_MODEL_TYPE)


@dataclass
class ModelMap:
    base: type[_p.BaseModel]
    db_model: type[SQLModel]
    model_links: Sequence[type[SQLModel]]
    output: type[_p.BaseModel]


GuruMap = ModelMap(
    base=guru.GuruBase,
    db_model=guru.Guru,
    model_links=[links.GuruEpisodeLink, links.RedditThreadGuruLink],
    output=responses.GuruOut
)

EpisodeMap = ModelMap(
    base=episodedb.EpisodeBase,
    db_model=episodedb.Episode,
    model_links=[links.GuruEpisodeLink, links.RedditThreadEpisodeLink],
    output=responses.EpisodeOut
)

RedditThreadMap = ModelMap(
    base=reddit_thread.RedditThreadBase,
    db_model=reddit_thread.RedditThread,
    model_links=[links.RedditThreadEpisodeLink, links.RedditThreadGuruLink],
    output=responses.RedditThreadOut
)

models_map = {
    'guru': GuruMap,
    'episode': EpisodeMap,
    'reddit_thread': RedditThreadMap,
}
