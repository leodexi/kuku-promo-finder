"""Serialization and presentation helpers (no Streamlit dependency)."""

import csv
import io
import json
from typing import Any

from .models import Candidate, candidate_to_dict


def candidate_rows(candidates: list[Candidate]) -> list[dict[str, Any]]:
    rows = []
    for rank, item in enumerate(candidates, 1):
        rows.append({"Rank": rank, "Episode": item.episode, "Start Timestamp": item.start_timestamp,
                     "End Timestamp": item.end_timestamp, "Duration (seconds)": item.duration_seconds,
                     "Segments": " + ".join(f"{s.start}–{s.end}" for s in item.segments),
                     "The Hook (First 3s)": item.hook, "The Cliffhanger": item.cliffhanger,
                     "Why It Works": item.why_it_works})
    return rows


def to_csv(rows: list[dict[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    fields = list(rows[0]) if rows else ["Rank", "Episode", "Start Timestamp", "End Timestamp", "Duration (seconds)", "Segments", "The Hook (First 3s)", "The Cliffhanger", "Why It Works"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def to_json(candidates: list[Candidate]) -> bytes:
    return json.dumps([candidate_to_dict(item, rank) for rank, item in enumerate(candidates, 1)], ensure_ascii=False, indent=2).encode("utf-8")
