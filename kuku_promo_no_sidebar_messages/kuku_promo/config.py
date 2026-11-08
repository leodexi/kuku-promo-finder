"""Application defaults, environment loading, and shared configuration."""

from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _env_file in (_PROJECT_ROOT / ".env", Path.cwd() / ".env", Path(__file__).resolve().parent / ".env"):
    if _env_file.is_file():
        load_dotenv(_env_file, override=False)

APP_TITLE = "Kuku Microdrama Promo Finder"
DEFAULT_MODELS = {"Google Gemini": "gemini-flash-latest", "OpenAI": "gpt-4o-mini"}
API_KEY_VARIABLES = {"Google Gemini": "GEMINI_API_KEY", "OpenAI": "OPENAI_API_KEY"}
MAX_ZIP_MEMBER_BYTES = 10_000_000
MAX_UPLOAD_BYTES = 100_000_000
MAX_PROMO_SECONDS = 60.0
MIN_PROMO_SECONDS = 20.0
