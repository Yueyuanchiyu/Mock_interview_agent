from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.core.config import settings


_initialized = False


def _initialize() -> None:
    global _initialized
    if _initialized:
        return

    root = logging.getLogger("app")
    root.setLevel(logging.INFO)
    root.propagate = False
    if root.handlers:
        _initialized = True
        return

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        settings.log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(console)
    root.addHandler(file_handler)
    _initialized = True


class Logger:
    @classmethod
    def get_logger(cls, name: str = __name__) -> logging.Logger:
        _initialize()
        return logging.getLogger(name)

