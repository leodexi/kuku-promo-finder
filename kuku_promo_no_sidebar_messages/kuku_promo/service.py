"""Application use case: extract, validate, and rank promos across episodes."""

from typing import Callable

from .models import AnalysisResult, Candidate
from .prompts import extraction_prompt, ranking_prompt
from .providers import LLMProvider
from .validation import validate_candidate


def analyze_episodes(episodes: list[dict], provider: LLMProvider, model: str,
                    max_per_episode: int, progress: Callable[[int, int, str], None] | None = None) -> AnalysisResult:
    accepted: list[Candidate] = []
    rejected: list[dict[str, str]] = []
    raw_outputs: list[dict] = []
    for episode_index, episode in enumerate(episodes, start=1):
        if progress:
            progress(episode_index, len(episodes) + 1, f"Analyzing {episode['episode']}")
        if not episode["blocks"]:
            rejected.append({"episode": episode["episode"], "candidate": "", "reason": "No timestamped Start/End blocks found."})
            continue
        try:
            response = provider.generate_json(model, extraction_prompt(episode, max_per_episode))
            raw_outputs.append({"episode": episode["episode"], "response": response})
            proposals = response.get("candidates", [])
            if not isinstance(proposals, list):
                raise ValueError("Response did not contain a candidates list.")
            for index, item in enumerate(proposals, 1):
                candidate, reason = validate_candidate(item, episode, index) if isinstance(item, dict) else (None, "Candidate was not a JSON object.")
                if candidate:
                    accepted.append(candidate)
                else:
                    rejected.append({"episode": episode["episode"], "candidate": str(index), "reason": reason or "Validation failed."})
        except Exception as exc:
            rejected.append({"episode": episode["episode"], "candidate": "", "reason": f"Model request failed: {type(exc).__name__}: {exc}"})

    rank_note = ""
    if accepted:
        if progress:
            progress(len(episodes) + 1, len(episodes) + 1, "Ranking accepted promos across episodes")
        try:
            ranked = provider.generate_json(model, ranking_prompt(accepted))
            raw_outputs.append({"stage": "global_ranking", "response": ranked})
            rank_note = str(ranked.get("notes", ""))
            by_id = {candidate.candidate_id: candidate for candidate in accepted}
            ids = ranked.get("ranked_ids", [])
            ordered = []
            for candidate_id in ids if isinstance(ids, list) else []:
                if candidate_id in by_id and by_id[candidate_id] not in ordered:
                    ordered.append(by_id[candidate_id])
            ordered.extend(candidate for candidate in accepted if candidate not in ordered)
            accepted = ordered
        except Exception as exc:
            rank_note = f"Global ranking unavailable; ranked by episode score. {type(exc).__name__}: {exc}"
            accepted.sort(key=lambda item: item.score, reverse=True)
    return AnalysisResult(accepted, rejected, raw_outputs, rank_note)
