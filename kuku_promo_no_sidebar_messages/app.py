"""Streamlit presentation layer for Kuku Microdrama Promo Finder."""

from __future__ import annotations

import streamlit as st
import os

from kuku_promo.config import API_KEY_VARIABLES, APP_TITLE, DEFAULT_MODELS
from kuku_promo.history import load_latest, save_latest
from kuku_promo.ingestion import load_scripts, parse_episode
from kuku_promo.presentation import candidate_rows, to_csv, to_json
from kuku_promo.providers import get_provider
from kuku_promo.service import analyze_episodes


def render_results() -> None:
    candidates = st.session_state["promo_candidates"]
    rejected = st.session_state["promo_rejected"]
    rows = candidate_rows(candidates)
    st.subheader("Ranked promos")
    st.caption(f"{len(candidates)} validated candidate(s) across {st.session_state['episode_count']} episode(s). Duration sums selected segments; gaps are excluded.")
    if st.session_state.get("rank_note"):
        st.caption(st.session_state["rank_note"])
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True, column_config={
            "Rank": st.column_config.NumberColumn(width="small"),
            "Duration (seconds)": st.column_config.NumberColumn(format="%.2f s", width="small"),
            "Segments": st.column_config.TextColumn(help="Playback intervals; gaps are not included in duration."),
        })
        left, right = st.columns(2)
        left.download_button("Download CSV", to_csv(rows), "kuku_promo_results.csv", "text/csv", use_container_width=True)
        right.download_button("Download JSON", to_json(candidates), "kuku_promo_results.json", "application/json", use_container_width=True)
    else:
        st.warning("No candidates passed validation. Check timestamp formatting or try another batch.")
    if rejected:
        with st.expander(f"Rejected or skipped candidates ({len(rejected)})"):
            st.dataframe(rejected, hide_index=True, use_container_width=True)
    with st.expander("Raw model output and editor notes"):
        st.caption("Returned JSON and concise editorial notes are shown here; private chain-of-thought is not requested.")
        st.json(st.session_state["raw_outputs"])


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🎬", layout="wide")
    st.title("🎬 Kuku Microdrama Promo Finder")
    st.caption("Find and rank 20–60 second promos from timestamped screenplay files.")
    st.info("Screenplay text is sent to the selected model provider when analysis runs. Upload only content you are authorized to share with that provider.")
    with st.sidebar:
        st.header("Model settings")
        provider_name = st.selectbox("LLM provider", list(DEFAULT_MODELS))
        model_name = st.text_input("Model", DEFAULT_MODELS[provider_name], help="Use a model supported by this provider's JSON output mode.")
        key_variable = API_KEY_VARIABLES[provider_name]
        key_is_set = bool(os.getenv(key_variable, "").strip())
    if "promo_candidates" not in st.session_state:
        try:
            saved = load_latest()
            if saved:
                st.session_state["promo_candidates"] = saved["candidates"]
                st.session_state["promo_rejected"] = saved["rejected"]
                st.session_state["raw_outputs"] = saved["raw_outputs"]
                st.session_state["rank_note"] = saved["rank_note"]
                st.session_state["episode_count"] = saved["episode_count"]
        except Exception as exc:
            st.warning(f"Could not restore the saved results: {exc}")
    uploads = st.file_uploader("Upload screenplay files", type=["txt", "zip"], accept_multiple_files=True,
                               help="Choose one or more TXT files or a ZIP containing TXT scripts.")
    per_episode = st.slider("Maximum promos to request per episode", 1, 5, 3)
    submitted = st.button("Find & Rank Promos", type="primary", disabled=not uploads or not key_is_set)
    if submitted:
        scripts, warnings = load_scripts(uploads or [])
        for warning in warnings:
            st.warning(warning)
        if not scripts:
            st.error("No readable .txt screenplay files were found.")
        else:
            episodes = [parse_episode(name, text) for name, text in scripts]
            st.write(f"Parsed **{len(episodes)}** episode file(s).")
            progress_bar = st.progress(0, text="Preparing analysis…")

            def update_progress(current: int, total: int, label: str) -> None:
                progress_bar.progress(min(current / total, 1.0), text=label)

            with st.spinner("Analyzing the screenplay batch…"):
                result = analyze_episodes(episodes, get_provider(provider_name), model_name.strip(), per_episode, update_progress)
            progress_bar.empty()
            st.session_state["promo_candidates"] = result.candidates
            st.session_state["promo_rejected"] = result.rejected
            st.session_state["raw_outputs"] = result.raw_outputs
            st.session_state["rank_note"] = result.rank_note
            st.session_state["episode_count"] = len(episodes)
            try:
                save_latest(result.candidates, result.rejected, result.raw_outputs, result.rank_note, len(episodes))
            except Exception as exc:
                st.warning(f"Results are available for this session but could not be saved locally: {exc}")
    if "promo_candidates" in st.session_state:
        render_results()


if __name__ == "__main__":
    main()
