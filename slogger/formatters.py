"""
Custom log formatters for slogger.
"""

import json
import logging
from datetime import datetime, timezone


class ColorFormatter(logging.Formatter):
    """
    ANSI-colored console formatter.
    
    Applies color codes based on log level:
    - DEBUG: cyan
    - INFO: green
    - WARNING: yellow
    - ERROR: red
    - CRITICAL: bold red
    """
    
    COLORS = {
        logging.DEBUG: "\033[36m",      # cyan
        logging.INFO: "\033[32m",       # green
        logging.WARNING: "\033[33m",    # yellow
        logging.ERROR: "\033[31m",      # red
        logging.CRITICAL: "\033[1;31m", # bold red
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        reset = self.RESET
        
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}{record.levelname:<8}{reset}"
        location = f"{record.filename}:{record.lineno}"
        message = record.getMessage()
        
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            message = f"{message}\n{exc_text}"
        
        return f"{timestamp} | {level} | {location} | {message}"


class JsonFormatter(logging.Formatter):
    """
    Structured JSON formatter.
    
    Outputs each log record as a single JSON line with fields:
    - timestamp (ISO 8601 UTC)
    - level
    - logger
    - module
    - function
    - line
    - message
    - exception (if present)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(data, ensure_ascii=False)
