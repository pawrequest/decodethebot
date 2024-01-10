from __future__ import annotations  # yes here

import inspect
from typing import Sequence, TYPE_CHECKING

from loguru import logger
if TYPE_CHECKING:
    from DecodeTheBot.models.episode_ext import Episode


def log_episodes(eps: Sequence[Episode], calling_func=None, msg: str = "", bot_name="General"):
    """Logs the first 3 episodes and the last 2 episodes of a sequence of any episode type"""
    if not eps:
        return
    if calling_func:
        calling_f = calling_func.__name__
    else:
        calling_f = f"{inspect.stack()[1].function} INSPECTED, YOU SHOULD PROVIDE THE FUNC"

    new_msg = f"{msg} {len(eps)} Episodes in {calling_f}():\n"
    new_msg += episode_log_msg(eps)
    logger.info(new_msg, bot_name=bot_name)


def episode_log_msg(eps: Sequence[Episode]) -> str:
    msg = ""  # in case no eps
    msg += "\n".join([_.log_str() for _ in eps[:3]])

    if len(eps) == 4:
        fth = eps[3]
        msg += f"\n{fth.log_str()}"
    elif len(eps) > 4:
        to_log = min([2, abs(len(eps) - 4)])
        msg += " \n\t... more ...\n"
        msg += "\n".join([_.log_str() for _ in eps[-to_log:]])
    return msg
