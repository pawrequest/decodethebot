from __future__ import annotations

import sys
from typing import Literal

from loguru import logger


def get_logger(log_file, profile: Literal["local", "remote", "default"] = None) -> logger:
    if profile == "local":
        logger.info("Using local log profile")
        terminal_format = log_fmt_local_terminal
    elif profile == "remote":
        logger.info("Using remote log profile")
        terminal_format = log_fmt_server_terminal
    elif profile is None:
        logger.info("Using default log profile (remote)")
        terminal_format = log_fmt_server_terminal
    else:
        raise ValueError(f"Invalid profile: {profile}")

    logger.remove()

    logger.add(log_file, rotation="1 day", delay=True)
    logger.add(sys.stdout, level="DEBUG", format=terminal_format)

    return logger


BOT_COLOR = {
    "Scraper": "cyan",
    "Monitor": "green",
    "Backup": "magenta",
}


def log_fmt_local_terminal(record):
    bot_name = record["extra"].get("bot_name", "General")
    bot_colour = BOT_COLOR.get(bot_name, "white")
    bot_name = f"{bot_name:<9}"
    max_length = 80
    file_txt = f"{record['file'].path}:{record['line']}"

    if len(file_txt) > max_length:
        file_txt = file_txt[:max_length]

    # clickable link only works at start of line
    return f"{file_txt:<{max_length}} | <lvl>{record['level']: <7} | {coloured(bot_name, bot_colour)} | {record['message']}</lvl>\n"


def coloured(msg: str, colour: str) -> str:
    return f"<{colour}>{msg}</{colour}>"


def log_fmt_server_terminal(record):
    """Format for server-side logging"""
    bot_name = record["extra"].get("bot_name", "General")
    bot_name = f"{bot_name:<9}"
    bot_colour = BOT_COLOR.get(bot_name, "white")

    file_line = f"{record['file']}:{record['line']}- {record['function']}()"
    bot_says = f"<bold>{coloured(bot_name, bot_colour):<9} </bold> | {coloured(record['message'], bot_colour)}"

    return f"<lvl>{record['level']: <7} </lvl>| {bot_says} | {file_line}\n"
