from dataclasses import dataclass
from typing import Sequence, TypeVar, Union

from sqlmodel import SQLModel
import pydantic as _p

from DecodeTheBot.models import episode_m, guru_m, links, reddit_m, responses

DB_MODELS = (guru_m.Guru, episode_m.Episode, reddit_m.RedditThread)
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
    base=guru_m.GuruBase,
    db_model=guru_m.Guru,
    model_links=[links.GuruEpisodeLink, links.RedditThreadGuruLink],
    output=responses.GuruOut
)

EpisodeMap = ModelMap(
    base=episode_m.EpisodeBase,
    db_model=episode_m.Episode,
    model_links=[links.GuruEpisodeLink, links.RedditThreadEpisodeLink],
    output=responses.EpisodeOut
)

RedditThreadMap = ModelMap(
    base=reddit_m.RedditThreadBase,
    db_model=reddit_m.RedditThread,
    model_links=[links.RedditThreadEpisodeLink, links.RedditThreadGuruLink],
    output=responses.RedditThreadOut
)

models_map = {
    'guru': GuruMap,
    'episode': EpisodeMap,
    'reddit_thread': RedditThreadMap,
}
