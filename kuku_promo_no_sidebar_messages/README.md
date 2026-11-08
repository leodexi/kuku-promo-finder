# Kuku Microdrama Promo Finder

A layered Streamlit application for finding candidate 20–60 second promos in timestamped episode screenplays. The UI, file ingestion, prompt construction, model adapters, business rules, workflow, and export formatting live in separate modules. `app.py` is the presentation entry point.

## Project structure

```text
outputs/
├── app.py                     # Streamlit UI and wiring
├── requirements.txt           # Runtime dependencies
└── kuku_promo/
    ├── config.py              # Defaults and limits
    ├── ingestion.py           # TXT/ZIP loading and screenplay parser
    ├── models.py              # Domain data structures
    ├── prompts.py              # Extraction and ranking prompts
    ├── providers.py           # Gemini/OpenAI adapters
    ├── service.py             # Analyze → validate → rank workflow
    ├── validation.py          # Deterministic promo rules
    └── presentation.py        # CSV/JSON serialization
```

This separation keeps provider SDK changes isolated from the UI and business rules. A new model provider can be added in `providers.py` without moving parsing or validation logic.

## Run locally

1. Install Python 3.10 or newer.
2. In a terminal, change into the `outputs` folder containing `app.py` and `requirements.txt`.
3. Create and activate a virtual environment (recommended):

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS / Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install dependencies and launch:

   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

5. Choose a provider, upload one or more `.txt` scripts or a `.zip` containing `.txt` scripts, then click **Find & Rank Promos**.

### Configure the API key in the backend

The app reads the selected provider key from environment variables; it does not accept API keys in the browser. Copy `.env.example` to `.env` beside `app.py` and set one of these values:

```dotenv
GEMINI_API_KEY=your_actual_key
# or
OPENAI_API_KEY=your_actual_key
```

Restart Streamlit after editing `.env`. Keep `.env` private and out of Git. The sidebar reports whether the selected provider's variable is configured.

## Google Colab

1. Upload `app.py` and `requirements.txt` to the Colab notebook session using the Files pane, or place them in the notebook's working directory.
2. Run these cells:

   ```python
   %pip install -r requirements.txt
   !streamlit run app.py --server.port 8501 --server.headless true &
   ```

   ```python
   from google.colab import output
   output.serve_kernel_port_as_window(8501)
   ```

3. Set the appropriate environment variable in the notebook before starting Streamlit. Avoid sharing the notebook or its app URL while it is running.

## Deploy

- **Streamlit Community Cloud:** push the contents of this folder to a Git repository, create an app from that repository, and set `app.py` as the entry point. Commit the complete `kuku_promo/` package alongside it.
- **Hugging Face Spaces:** create a Streamlit Space, upload these files, and select `app.py` as the app file if prompted.
- Users enter their own provider API key in the sidebar. Provider free quotas and model availability vary; the model name can be edited in the sidebar.

## How the checks work

- `kuku_promo.ingestion` reads `EPISODE NUMBER`, `EPISODE LOGLINE`, and timestamp pairs formatted like `Start: (MM:SS.SS) | End: (MM:SS.SS)`. ZIP contents are read in memory, and individual uploads and members have size limits.
- Models propose one to three segments. Each segment must use start/end values present in the parsed screenplay. The sum of segment lengths must be **at least 20.0 and at most 60.0 seconds**, inclusive. Invalid or out-of-range proposals are rejected and shown in the app.
- The app also requires the model to affirm that the hook lands within the first three viewed seconds and that the promo stands alone for a cold audience. Those semantic checks still need editor review.
- `kuku_promo.service` coordinates episode extraction and global ranking. The ranking call sees only validated candidates. If it fails, the app retains per-episode scores and sorts by those instead.
- `kuku_promo.presentation` creates CSV and JSON exports with rank, episode, timestamps, segment list, duration, hook, cliffhanger, and rationale. The expandable raw-output panel preserves returned JSON and validation failures for review.
- The most recent completed result is saved in a local SQLite database under `data/` so it survives a browser refresh on the same computer. The API key and uploaded source scripts are not saved. The local database contains promo text and model output; remove `data/promo_history.sqlite3` to clear it.

## Assumptions and limits

- The input is screenplay text with one timestamp pair per shot, action, or dialogue beat. A model-selected segment must start and end on one of these exact timestamp boundaries; a valid editorial cut inside a beat is therefore rejected.
- The runtime is the sum of segment durations. Gaps between non-contiguous segments are excluded. The displayed start and end timestamps bound the first and last segments; use the `Segments` column to see each selected interval.
- The app asks for a hook in the first three seconds and standalone comprehension, but those are editorial judgments. Review the selected beat text against the source before publishing. It does not view rendered video, verify visual continuity, or guarantee ad performance.
- Screenplay text is sent to the provider selected in the sidebar. Do not upload content unless you are authorized to send it to that provider.
- For a full 50-episode pack, expect one extraction call per episode plus one global ranking call. Provider rate limits, context limits, and network failures can cause individual episode calls to fail; failures are visible in the rejected/skipped table. Reduce batch size if your provider limits requests.
- Keep the model editable: providers can retire model names and change free-tier availability. Gemini defaults to the current `gemini-flash-latest` alias; OpenAI defaults to `gpt-4o-mini`.
