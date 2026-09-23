"""Single place that configures logging: rotating file + concise console."""
from __future__ import annotations

import logging
import logging.handlers
import sys

from . import config

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    _configured = True
    root = logging.getLogger("ssb")
    root.setLevel(logging.INFO)
    root.propagate = False

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)-12s %(message)s", "%Y-%m-%d %H:%M:%S")
    try:
        fh = logging.handlers.RotatingFileHandler(
            config.LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        root.addHandler(fh)
    except OSError:
        pass

    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(logging.Formatter("  %(levelname)-7s %(message)s"))
    ch.setLevel(logging.INFO)
    root.addHandler(ch)


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger("ssb." + name)
