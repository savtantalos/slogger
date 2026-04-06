"""
Tests for savvas_logger.Logger class.
Run with:  pytest tests/ -v
"""

import json
import logging
import os
import tempfile

import pytest

from savvas_logger import Logger, ColorFormatter, JsonFormatter, SMTPConfig


# ── in-memory handler ─────────────────────────────────────────────────────────

class _MemoryHandler(logging.Handler):
    def __init__(self, store: list):
        super().__init__(logging.DEBUG)
        self._store = store

    def emit(self, record: logging.LogRecord):
        self._store.append(record)


def _clear(name: str) -> None:
    logging.getLogger(name).handlers.clear()


# ── instantiation ─────────────────────────────────────────────────────────────

class TestInstantiation:
    def test_no_args_works(self):
        log = Logger()
        assert log is not None

    def test_auto_name_starts_with_prefix(self):
        log = Logger()
        assert log.name.startswith("logger-")

    def test_explicit_name(self):
        _clear("t-name")
        log = Logger(name="t-name")
        assert log.name == "t-name"

    def test_level_property(self):
        _clear("t-level")
        log = Logger(name="t-level", level="WARNING")
        assert log.level == "WARNING"

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            Logger(level="VERBOSE")

    def test_repr_contains_name(self):
        _clear("t-repr")
        log = Logger(name="t-repr")
        assert "t-repr" in repr(log)

    def test_log_to_file_no_path_raises(self):
        with pytest.raises(ValueError, match="log_file"):
            Logger(log_to_file=True)


# ── handlers ──────────────────────────────────────────────────────────────────

class TestHandlers:
    def test_console_handler_by_default(self):
        _clear("h-con")
        log = Logger(name="h-con")
        stream = [h for h in log.handlers
                  if isinstance(h, logging.StreamHandler)
                  and not isinstance(h, logging.FileHandler)]
        assert len(stream) == 1

    def test_no_handlers_when_console_off(self):
        _clear("h-off")
        log = Logger(name="h-off", log_to_console=False)
        assert len(log.handlers) == 0

    def test_file_handler_attached(self):
        _clear("h-file")
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            path = f.name
        try:
            log = Logger(name="h-file", log_to_console=False,
                         log_to_file=True, log_file=path, rotation=None)
            assert any(isinstance(h, logging.FileHandler) for h in log.handlers)
        finally:
            _clear("h-file")
            os.unlink(path)

    def test_idempotent_handlers_on_same_name(self):
        _clear("h-idem")
        Logger(name="h-idem")
        Logger(name="h-idem")
        assert len(logging.getLogger("h-idem").handlers) == 1


# ── logging methods ───────────────────────────────────────────────────────────

class TestLoggingMethods:
    def _make(self, name: str):
        _clear(name)
        records = []
        log = Logger(name=name, log_to_console=False)
        logging.getLogger(name).addHandler(_MemoryHandler(records))
        return log, records

    def test_debug(self):
        log, recs = self._make("m-debug")
        log.debug("dbg")
        assert any(r.getMessage() == "dbg" for r in recs)

    def test_info(self):
        log, recs = self._make("m-info")
        log.info("info")
        assert any(r.levelno == logging.INFO for r in recs)

    def test_warning(self):
        log, recs = self._make("m-warn")
        log.warning("warn")
        assert any(r.levelno == logging.WARNING for r in recs)

    def test_error(self):
        log, recs = self._make("m-err")
        log.error("err")
        assert any(r.levelno == logging.ERROR for r in recs)

    def test_critical(self):
        log, recs = self._make("m-crit")
        log.critical("crit")
        assert any(r.levelno == logging.CRITICAL for r in recs)

    def test_set_level(self):
        _clear("m-setlvl")
        log = Logger(name="m-setlvl", log_to_console=False)
        log.set_level("ERROR")
        assert log.level == "ERROR"

    def test_exception_attaches_traceback(self):
        log, recs = self._make("m-exc")
        try:
            raise ValueError("boom")
        except ValueError:
            log.exception("caught")
        assert any(r.exc_info is not None for r in recs)


# ── formatters ────────────────────────────────────────────────────────────────

class TestColorFormatter:
    def _rec(self, level=logging.INFO, msg="hello"):
        return logging.LogRecord("myapp", level, "", 42, msg, (), None)

    def test_contains_message(self):
        assert "hello" in ColorFormatter().format(self._rec())

    def test_contains_level_name(self):
        assert "WARNING" in ColorFormatter().format(self._rec(level=logging.WARNING))

    def test_ansi_escape_codes_present(self):
        assert "\033[" in ColorFormatter().format(self._rec())


class TestJsonFormatter:
    def _parse(self, level=logging.ERROR, msg="oops") -> dict:
        rec = logging.LogRecord("svc", level, "app.py", 99, msg, (), None)
        return json.loads(JsonFormatter().format(rec))

    def test_valid_json(self):
        self._parse()

    def test_required_fields_present(self):
        data = self._parse()
        for field in ("timestamp", "level", "logger", "module", "function", "line", "message"):
            assert field in data, f"Missing: {field}"

    def test_level_value(self):
        assert self._parse(level=logging.ERROR)["level"] == "ERROR"

    def test_message_value(self):
        assert self._parse(msg="test msg")["message"] == "test msg"

    def test_timestamp_ends_with_z(self):
        assert self._parse()["timestamp"].endswith("Z")


# ── integration: file write + read ───────────────────────────────────────────

class TestFileIntegration:
    def test_json_log_written_correctly(self):
        name = "intg-json"
        _clear(name)
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            path = f.name
        try:
            log = Logger(name=name, log_to_console=False,
                         log_to_file=True, log_file=path,
                         log_format="json", rotation=None)
            log.warning("integration check")
            for h in log.handlers:
                h.flush()
            with open(path) as fh:
                lines = [l.strip() for l in fh if l.strip()]
            data = json.loads(lines[-1])
            assert data["message"] == "integration check"
            assert data["level"] == "WARNING"
        finally:
            _clear(name)
            os.unlink(path)

    def test_plain_log_written_correctly(self):
        name = "intg-plain"
        _clear(name)
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            path = f.name
        try:
            log = Logger(name=name, log_to_console=False,
                         log_to_file=True, log_file=path,
                         log_format="plain", rotation=None)
            log.error("plain write test")
            for h in log.handlers:
                h.flush()
            content = open(path).read()
            assert "plain write test" in content
        finally:
            _clear(name)
            os.unlink(path)


# ── SMTPConfig ────────────────────────────────────────────────────────────────

class TestSMTPConfig:
    def test_basic_instantiation(self):
        cfg = SMTPConfig(mailhost="smtp.example.com",
                         from_addr="a@b.com", to_addrs=["c@d.com"])
        assert cfg.credentials is None
        assert cfg.timeout == 5.0

    def test_with_tls_credentials(self):
        cfg = SMTPConfig(mailhost=("smtp.gmail.com", 587),
                         from_addr="me@gmail.com", to_addrs=["you@gmail.com"],
                         credentials=("user", "pass"), secure=())
        assert cfg.secure == ()
        assert len(cfg.credentials) == 2
