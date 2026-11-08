"""Hard business-rule checks for model-proposed promo moments."""

from __future__ import annotations

from typing import Any

from .config import MAX_PROMO_SECONDS, MIN_PROMO_SECONDS
from .ingestion import timestamp_seconds
from .models import Candidate, Segment


def validate_candidate(raw: dict[str, Any], episode: dict[str, Any], index: int) -> tuple[Candidate | None, str | None]:
    proposed = raw.get("segments")
    if not isinstance(proposed, list) or not 1 <= len(proposed) <= 3:
        return None, "Expected 1 to 3 timestamped segments."
    available = set(episode["timestamps"])
    segments: list[Segment] = []
    duration = 0.0
    previous_end = -1.0
    for item in proposed:
        if not isinstance(item, dict):
            return None, "A segment was not a JSON object."
        start, end = str(item.get("start", "")), str(item.get("end", ""))
        if start not in available or end not in available:
            return None, f"Timestamp {start}–{end} does not match parsed screenplay boundaries."
        start_s, end_s = timestamp_seconds(start), timestamp_seconds(end)
        if end_s <= start_s or start_s < previous_end:
            return None, "Segments must be positive-length, chronological, and non-overlapping."
        duration += end_s - start_s
        previous_end = end_s
        segments.append(Segment(start, end))
    if duration < MIN_PROMO_SECONDS:
        return None, f"Duration {duration:.2f}s is under the {MIN_PROMO_SECONDS:.1f}-second minimum."
    if duration > MAX_PROMO_SECONDS:
        return None, f"Duration {duration:.2f}s is over the {MAX_PROMO_SECONDS:.1f}-second maximum."
    hook, cliffhanger, why = (str(raw.get(key, "")).strip() for key in ("hook", "cliffhanger", "why_it_works"))
    if not hook or not cliffhanger or not why:
        return None, "Hook, cliffhanger, and rationale must all be present."
    if raw.get("hook_within_first_3s") is not True:
        return None, "The model did not confirm a hook within the first three seconds."
    if raw.get("standalone") is not True:
        return None, "The model did not confirm cold-audience clarity."
    try:
        score = max(1.0, min(100.0, float(raw.get("score", 50))))
    except (TypeError, ValueError):
        score = 50.0
    return Candidate(
        candidate_id=f"{episode['filename']}::candidate-{index}", episode=episode["episode"],
        segments=segments, start_timestamp=segments[0].start, end_timestamp=segments[-1].end,
        duration_seconds=round(duration, 2), hook=hook, cliffhanger=cliffhanger,
        why_it_works=why, score=score, standalone=True,
        model_notes=str(raw.get("model_notes", "")),
    ), None
