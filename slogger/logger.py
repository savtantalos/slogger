"""
Core logger implementation for slogger.
"""

import inspect
import logging
import sys
import uuid
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional

from .formatters import ColorFormatter, JsonFormatter
from .handlers import SMTPConfig, build_smtp_handler


# ── project-root detection ────────────────────────────────────────────────────

def _resolve_log_file() -> Path:
    """
    Walk up the call stack to find the file that instantiated Logger,
    then anchor the log output inside that project's root folder.

    Strategy
    --------
    1. Find the first frame OUTSIDE slogger — that is the caller's file.
       e.g. /home/savvas/myproject/services/user.py
    2. Walk up its directory tree looking for a project-root marker:
       pyproject.toml, setup.py, setup.cfg, or .git
    3. If a marker is found → project root is that directory.
    4. If no marker is found → fall back to the caller file's own directory.
    5. Return  <project_root>/output.logs/<project_name>.log

    Example
    -------
    Project at  /home/savvas/myproject/   (has pyproject.toml)
    Caller      /home/savvas/myproject/services/user.py
    Log file  → /home/savvas/myproject/output.logs/myproject.log
    """
    _ROOT_MARKERS = {"pyproject.toml", "setup.py", "setup.cfg", ".git"}
    _THIS_PACKAGE = Path(__file__).parent.resolve()

    # Step 1: find the first frame outside slogger
    caller_file: Optional[Path] = None
    for frame_info in inspect.stack():
        frame_path = Path(frame_info.filename).resolve()
        try:
            frame_path.relative_to(_THIS_PACKAGE)
            continue          # still inside our package — skip
        except ValueError:
            pass              # outside our package — this is the caller
        if frame_path.suffix == ".py":
            caller_file = frame_path
            break

    if caller_file is None:
        caller_file = Path.cwd() / "script.py"   # REPL fallback

    # Step 2: walk up to find the project root
    project_root: Optional[Path] = None
    for parent in [caller_file.parent, *caller_file.parent.parents]:
        if any((parent / marker).exists() for marker in _ROOT_MARKERS):
            project_root = parent
            break

    if project_root is None:
        project_root = caller_file.parent        # fallback: caller's own dir

    # Step 3: build the path
    project_name = project_root.name
    return project_root / "output.logs" / f"{project_name}.log"


# ── Logger class ──────────────────────────────────────────────────────────────

class Logger:
    """
    A self-contained logger you can instantiate and use directly.

    Wraps Python's :class:`logging.Logger` and exposes ``debug``, ``info``,
    ``warning``, ``error``, ``critical``, and ``exception`` as first-class
    methods.

    File output
    -----------
    When ``log_to_file=True`` and no ``log_file`` path is given, the log file
    is placed automatically at::

        <project_root>/output.logs/<project_name>.log

    The project root is detected by walking up from the calling file until a
    ``pyproject.toml``, ``setup.py``, ``setup.cfg``, or ``.git`` is found.

    Parameters
    ----------
    name : str | None
        Logger name (appears in the ``"logger"`` field of JSON output and in
        Python's global logger registry).  Auto-generated when omitted.
    level : str
        Minimum log level: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    log_to_console : bool
        Stream log records to stdout.
    log_to_file : bool
        Write log records to a file.
    log_file : str | None
        Explicit log file path.  When omitted, auto-detected from the
        project root (see above).
    rotation : str | None
        ``"size"`` — rotate on ``max_bytes``.
        ``"time"`` — rotate on a schedule (``when``).
        ``None``   — no rotation.
    max_bytes : int
        File size cap before rotation (``rotation="size"``).
    backup_count : int
        Rotated files to keep.
    when : str
        Rotation schedule for ``rotation="time"`` (e.g. ``"midnight"``).
    log_format : str
        ``"color"`` — ANSI-coloured console output.
        ``"json"``  — structured JSON lines.
        ``"plain"`` — plain text without colours.
    smtp_config : SMTPConfig | None
        Email config for CRITICAL-level alerts.
    propagate : bool
        Whether records bubble up to the root logger.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        level: str = "DEBUG",
        *,
        log_to_console: bool = True,
        log_to_file: bool = False,
        log_file: Optional[str] = None,
        rotation: str = "size",
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 3,
        when: str = "midnight",
        log_format: str = "color",
        smtp_config: Optional[SMTPConfig] = None,
        propagate: bool = False,
    ) -> None:
        self._name  = name or f"logger-{uuid.uuid4().hex[:6]}"
        self._level = _parse_level(level)

        self._logger = logging.getLogger(self._name)

        if not self._logger.handlers:
            self._logger.setLevel(self._level)
            self._logger.propagate = propagate

            # Resolve log file path if file logging is enabled
            resolved_log_file: Optional[Path] = None
            if log_to_file:
                resolved_log_file = Path(log_file) if log_file else _resolve_log_file()

            self._log_file = resolved_log_file
            self._attach_handlers(
                log_to_console=log_to_console,
                log_to_file=log_to_file,
                log_file=resolved_log_file,
                rotation=rotation,
                max_bytes=max_bytes,
                backup_count=backup_count,
                when=when,
                log_format=log_format,
                smtp_config=smtp_config,
            )
        else:
            self._log_file = None

    # ── public logging methods ────────────────────────────────────────────────

    def debug(self, msg: object, *args, **kwargs) -> None:
        """Log a DEBUG message."""
        self._logger.debug(msg, *args, stacklevel=2, **kwargs)

    def info(self, msg: object, *args, **kwargs) -> None:
        """Log an INFO message."""
        self._logger.info(msg, *args, stacklevel=2, **kwargs)

    def warning(self, msg: object, *args, **kwargs) -> None:
        """Log a WARNING message."""
        self._logger.warning(msg, *args, stacklevel=2, **kwargs)

    def error(self, msg: object, *args, **kwargs) -> None:
        """Log an ERROR message."""
        self._logger.error(msg, *args, stacklevel=2, **kwargs)

    def critical(self, msg: object, *args, **kwargs) -> None:
        """Log a CRITICAL message (also triggers SMTP if configured)."""
        self._logger.critical(msg, *args, stacklevel=2, **kwargs)

    def exception(self, msg: object, *args, **kwargs) -> None:
        """Log an ERROR with the current exception traceback attached."""
        self._logger.exception(msg, *args, stacklevel=2, **kwargs)

    # ── runtime control ───────────────────────────────────────────────────────

    def set_level(self, level: str) -> None:
        """Change the minimum log level at runtime."""
        self._logger.setLevel(_parse_level(level))

    # ── introspection ─────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        """The logger name (appears in JSON output and the registry)."""
        return self._name

    @property
    def level(self) -> str:
        """Current minimum log level as a string."""
        return logging.getLevelName(self._logger.level)

    @property
    def log_file(self) -> Optional[Path]:
        """Resolved path to the log file, or None if file logging is off."""
        return self._log_file

    @property
    def handlers(self) -> list:
        return list(self._logger.handlers)

    def __repr__(self) -> str:
        parts = [f"name={self._name!r}", f"level={self.level!r}",
                 f"handlers={len(self._logger.handlers)}"]
        if self._log_file:
            parts.append(f"log_file={str(self._log_file)!r}")
        return f"Logger({', '.join(parts)})"

    # ── internal setup ────────────────────────────────────────────────────────

    def _attach_handlers(
        self,
        *,
        log_to_console: bool,
        log_to_file: bool,
        log_file: Optional[Path],
        rotation: str,
        max_bytes: int,
        backup_count: int,
        when: str,
        log_format: str,
        smtp_config: Optional[SMTPConfig],
    ) -> None:
        plain_fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # ── console handler ───────────────────────────────────────────────────
        if log_to_console:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(self._level)
            if log_format == "color":
                ch.setFormatter(ColorFormatter())
            elif log_format == "json":
                ch.setFormatter(JsonFormatter())
            else:
                ch.setFormatter(plain_fmt)
            self._logger.addHandler(ch)

        # ── file handler ──────────────────────────────────────────────────────
        if log_to_file and log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)

            if rotation == "size":
                fh = RotatingFileHandler(
                    log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
                )
            elif rotation == "time":
                fh = TimedRotatingFileHandler(
                    log_file, when=when, backupCount=backup_count, encoding="utf-8"
                )
            else:
                fh = logging.FileHandler(log_file, encoding="utf-8")

            fh.setLevel(self._level)
            fh.setFormatter(JsonFormatter() if log_format == "json" else plain_fmt)
            self._logger.addHandler(fh)

        # ── smtp handler ──────────────────────────────────────────────────────
        if smtp_config:
            mh = build_smtp_handler(smtp_config)
            mh.setLevel(logging.CRITICAL)
            mh.setFormatter(plain_fmt)
            self._logger.addHandler(mh)


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_level(level: str) -> int:
    numeric = getattr(logging, level.upper(), None)
    if not isinstance(numeric, int):
        raise ValueError(f"Invalid log level: {level!r}")
    return numeric
