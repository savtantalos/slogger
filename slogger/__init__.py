"""
slogger
=======

A plug-and-play Python logging package with:
- ANSI-colour console output
- Structured JSON logging
- Size- or time-based log rotation
- Optional SMTP alerts for CRITICAL events

Quick start
-----------
>>> from slogger import Logger
>>> log = Logger(name=__name__, log_to_console=True, log_format="color")
>>> log.info("Hello from slogger!")
"""

from .logger import Logger
from .formatters import ColorFormatter, JsonFormatter
from .handlers import SMTPConfig

__all__ = [
    "Logger",
    "ColorFormatter",
    "JsonFormatter",
    "SMTPConfig",
]

__version__ = "0.1.0"
__author__  = "Savvas"
