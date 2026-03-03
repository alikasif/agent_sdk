"""Structured logging setup for the Agent SDK."""

from __future__ import annotations

import logging
import sys
from typing import Final

_DEFAULT_FORMAT: Final[str] = (
    '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure stdlib logging with structured JSON-like formatting.

    Parameters
    ----------
    level:
        Log level name (e.g. ``"DEBUG"``, ``"INFO"``).

    Returns
    -------
    logging.Logger
        The root ``agent_sdk`` logger.
    """
    logger = logging.getLogger("agent_sdk")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S"))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
