"""Global configuration for the multidisciplinary literature radar."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
WEB_DIR = Path(__file__).resolve().parent / "web"
DB_PATH = DATA_DIR / "papers.db"
HTTP_CACHE = DATA_DIR / "http_cache"
SETTINGS_PATH = ROOT / "settings.json"

for _d in (DATA_DIR, LOG_DIR, HTTP_CACHE):
    _d.mkdir(parents=True, exist_ok=True)

APP_NAME = "Literature Radar"
APP_VERSION = "1.1.0"

DEFAULTS = {
    # OpenAlex asks for an e-mail to place you in the fast "polite pool".
    # Any address works; it is only sent as a courtesy identifier.
    "contact_email": "ssb-radar@localhost",
    "server_host": "127.0.0.1",
    "server_port": 8756,
    # How far back a normal daily refresh looks (days).
    "refresh_window_days": 21,
    # How far back the very first run looks (days).
    "backfill_days": 90,
    # Auto-refresh when the newest successful refresh is older than this (hours).
    "auto_refresh_after_hours": 8,
    # Minimum relevance score (see classify.py) for a paper to be stored.
    "min_relevance": 3,
    # Journal tiers to ingest: 1 = flagship, 2 = leading, 3 = solid specialist.
    "max_journal_tier": 3,
    "open_browser": True,
    # Optional: a free developer key from https://dev.elsevier.com lets the app
    # fill in abstracts for Elsevier journals (Joule, J. Power Sources, Energy
    # Storage Materials, ...), which no free metadata API exposes.
    "elsevier_api_key": "",
}


def _load_settings() -> dict:
    cfg = dict(DEFAULTS)
    if SETTINGS_PATH.exists():
        try:
            user = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(user, dict):
                cfg.update({k: v for k, v in user.items() if k in DEFAULTS})
        except Exception:
            pass  # a malformed settings file must never stop the app
    for key in cfg:
        env = os.environ.get("SSB_" + key.upper())
        if env is None:
            continue
        proto = DEFAULTS[key]
        try:
            if isinstance(proto, bool):
                cfg[key] = env.strip().lower() in ("1", "true", "yes", "on")
            elif isinstance(proto, int):
                cfg[key] = int(env)
            else:
                cfg[key] = env
        except (TypeError, ValueError):
            pass
    return cfg


SETTINGS = _load_settings()


def get(key: str):
    return SETTINGS.get(key, DEFAULTS.get(key))


USER_AGENT = "{}/{} (+local; mailto:{})".format(APP_NAME.replace(" ", ""), APP_VERSION, get("contact_email"))
