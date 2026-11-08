"""Local persistence for the most recent analysis; API keys and source scripts are never stored."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .models import Candidate, Segment


def _database_path() -> Path:
    configured = os.environ.get("KUKU_PROMO_DB")
    path = Path(configured) if configured else Path(__file__).resolve().parent.parent / "data" / "promo_history.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_latest(candidates: list[Candidate], rejected: list[dict[str, str]], raw_outputs: list[dict[str, Any]],
                rank_note: str, episode_count: int) -> None:
    payload = {
        "candidates": [{**candidate.__dict__, "segments": [segment.__dict__ for segment in candidate.segments]} for candidate in candidates],
        "rejected": rejected,
        "raw_outputs": raw_outputs,
        "rank_note": rank_note,
        "episode_count": episode_count,
    }
    with sqlite3.connect(_database_path()) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS latest_result (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL)")
        connection.execute("INSERT INTO latest_result (id, payload) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET payload = excluded.payload", (json.dumps(payload, ensure_ascii=False),))


def load_latest() -> dict[str, Any] | None:
    path = _database_path()
    if not path.exists():
        return None
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT payload FROM latest_result WHERE id = 1").fetchone()
    if not row:
        return None
    payload = json.loads(row[0])
    payload["candidates"] = [Candidate(**{**item, "segments": [Segment(**part) for part in item["segments"]]}) for item in payload["candidates"]]
    return payload
