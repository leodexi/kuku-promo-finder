"""Typed domain objects shared across application layers."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Segment:
    start: str
    end: str


@dataclass
class Candidate:
    candidate_id: str
    episode: str
    segments: list[Segment]
    start_timestamp: str
    end_timestamp: str
    duration_seconds: float
    hook: str
    cliffhanger: str
    why_it_works: str
    score: float
    standalone: bool
    model_notes: str


@dataclass
class AnalysisResult:
    candidates: list[Candidate]
    rejected: list[dict[str, str]]
    raw_outputs: list[dict[str, Any]]
    rank_note: str = ""


def candidate_to_dict(candidate: Candidate, rank: int | None = None) -> dict[str, Any]:
    result = asdict(candidate)
    if rank is not None:
        result = {"rank": rank, **result}
    return result
