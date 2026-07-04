"""
Structured logging setup.
In development: coloured human-readable logs.
In production: JSON lines to stdout (compatible with Datadog/CloudWatch).
"""
import logging
import sys
import os
import json
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "session_id"):
            log_obj["session_id"] = record.session_id
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = record.latency_ms
        return json.dumps(log_obj, ensure_ascii=False)


class ColourFormatter(logging.Formatter):
    COLOURS = {
        "DEBUG":    "\033[36m",   # Cyan
        "INFO":     "\033[32m",   # Green
        "WARNING":  "\033[33m",   # Yellow
        "ERROR":    "\033[31m",   # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self.COLOURS.get(record.levelname, "")
        prefix = f"{colour}{record.levelname:<8}{self.RESET}"
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        name = record.name.split(".")[-1]  # last component only
        return f"{ts} {prefix} [{name}] {record.getMessage()}"


def setup_logging(level: str = "INFO", json_logs: bool = False):
    """
    Configure root logger. Call once at app startup.
    json_logs=True in production, False in development.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if json_logs or os.getenv("LOG_FORMAT") == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ColourFormatter())

    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ["httpx", "httpcore", "urllib3", "elasticsearch", "pinecone"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Auto-setup on import if running as a module
if __name__ != "__main__":
    setup_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        json_logs=os.getenv("LOG_FORMAT", "").lower() == "json",
    )
