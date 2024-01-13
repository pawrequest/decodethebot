from __future__ import annotations
from typing import Union

import dotenv

# UI_ELEMENT = Union[Guru, Episode, RedditThread]
PAGE_SIZE = int(dotenv.get_key(".env", "PAGE_SIZE")) or 20
