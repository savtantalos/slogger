# slogger

A plug-and-play Python logging package with:
- **ANSI-colored console output** for better readability
- **Structured JSON logging** for production environments
- **Size- or time-based log rotation** to manage disk usage
- **Optional SMTP alerts** for CRITICAL events

---

## Installation

### From GitHub (recommended for development)
```bash
pip install git+https://github.com/savtantalos/slogger.git@v0.1.0
```

### Local development install
```bash
git clone https://github.com/savtantalos/slogger.git
cd slogger
pip install -e .
```

---

## Quick Start

```python
from slogger import Logger

# Basic console logger with color output
log = Logger(name="myapp", log_format="color")
log.info("Application started")
log.warning("This is a warning")
log.error("Something went wrong")
```

### File logging with JSON format
```python
log = Logger(
    name="myapp",
    log_to_console=True,
    log_to_file=True,
    log_file="/var/log/myapp.log",
    log_format="json",
    rotation="size",
    max_bytes=10 * 1024 * 1024,  # 10 MB
    backup_count=5
)

log.info("This will be logged to both console and file")
```

### Auto-detected log file path
When `log_to_file=True` without specifying `log_file`, the logger automatically detects your project root and creates logs at:
```
<project_root>/output.logs/<project_name>.log
```

### SMTP alerts for critical errors
```python
from slogger import Logger, SMTPConfig

smtp_config = SMTPConfig(
    mailhost=("smtp.gmail.com", 587),
    from_addr="alerts@myapp.com",
    to_addrs=["admin@myapp.com"],
    credentials=("user", "password"),
    secure=()
)

log = Logger(name="myapp", smtp_config=smtp_config)
log.critical("Database connection failed!")  # Sends email
```

---

## Features

### Log Formats
- **`color`** — ANSI-colored output for terminals
- **`json`** — Structured JSON lines (timestamp, level, logger, module, function, line, message)
- **`plain`** — Plain text without colors

### Rotation Options
- **`size`** — Rotate when file reaches `max_bytes`
- **`time`** — Rotate on schedule (`when="midnight"`, `"H"`, `"D"`, etc.)
- **`None`** — No rotation

### Log Levels
- `DEBUG`
- `INFO`
- `WARNING`
- `ERROR`
- `CRITICAL`

---

## API Reference

### `Logger`
```python
Logger(
    name: str | None = None,
    level: str = "DEBUG",
    log_to_console: bool = True,
    log_to_file: bool = False,
    log_file: str | None = None,
    rotation: str = "size",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
    when: str = "midnight",
    log_format: str = "color",
    smtp_config: SMTPConfig | None = None,
    propagate: bool = False
)
```

**Methods:**
- `log.debug(msg, *args, **kwargs)`
- `log.info(msg, *args, **kwargs)`
- `log.warning(msg, *args, **kwargs)`
- `log.error(msg, *args, **kwargs)`
- `log.critical(msg, *args, **kwargs)`
- `log.exception(msg, *args, **kwargs)` — logs ERROR with traceback
- `log.set_level(level: str)` — change log level at runtime

**Properties:**
- `log.name` — logger name
- `log.level` — current log level
- `log.log_file` — resolved log file path (if file logging enabled)
- `log.handlers` — list of attached handlers

---

## Development

### Run tests
```bash
pip install pytest
pytest tests/ -v
```

### Install in editable mode
```bash
pip install -e .
```

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Author

**Savvas Tantalidis**

For issues or feature requests, please open an issue on [GitHub](https://github.com/savtantalos/slogger/issues).
