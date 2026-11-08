"""Safe in-memory loading and deterministic screenplay parsing."""

from __future__ import annotations

import io
import re
import zipfile
from typing import Any

from .config import MAX_UPLOAD_BYTES, MAX_ZIP_MEMBER_BYTES

TIMESTAMP_RE = re.compile(r"Start:\s*\((\d{1,3}:\d{2}(?:\.\d+)?)\)\s*\|\s*End:\s*\((\d{1,3}:\d{2}(?:\.\d+)?)\)", re.I)
EPISODE_RE = re.compile(r"^\s*EPISODE NUMBER:\s*(.+?)\s*$", re.I | re.M)
LOGLINE_RE = re.compile(r"^\s*EPISODE LOGLINE:\s*(.+?)\s*$", re.I | re.M)


def timestamp_seconds(value: str) -> float:
    minutes, seconds = value.split(":", 1)
    return int(minutes) * 60 + float(seconds)


def decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_scripts(uploads: list[Any]) -> tuple[list[tuple[str, str]], list[str]]:
    """Read user-provided TXT files and ZIP members without extracting to disk."""
    scripts: list[tuple[str, str]] = []
    warnings: list[str] = []
    for upload in uploads:
        if upload.size > MAX_UPLOAD_BYTES:
            warnings.append(f"Skipped {upload.name}: file exceeds the {MAX_UPLOAD_BYTES // 1_000_000} MB upload limit.")
            continue
        if upload.name.lower().endswith(".txt"):
            scripts.append((upload.name, decode_text(upload.getvalue())))
        elif upload.name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(upload.getvalue())) as archive:
                    for member in archive.infolist():
                        if member.is_dir() or not member.filename.lower().endswith(".txt"):
                            continue
                        if member.file_size > MAX_ZIP_MEMBER_BYTES:
                            warnings.append(f"Skipped {member.filename}: archive member exceeds 10 MB.")
                            continue
                        try:
                            scripts.append((member.filename, decode_text(archive.read(member))))
                        except (RuntimeError, OSError, zipfile.BadZipFile) as exc:
                            warnings.append(f"Could not read {member.filename}: {exc}")
            except (zipfile.BadZipFile, OSError) as exc:
                warnings.append(f"Could not read {upload.name}: {exc}")
    return [(name, text) for name, text in scripts if text.strip()], warnings


def parse_episode(filename: str, text: str) -> dict[str, Any]:
    episode_match, logline_match = EPISODE_RE.search(text), LOGLINE_RE.search(text)
    timestamps: set[str] = set()
    blocks: list[dict[str, str]] = []
    for match in TIMESTAMP_RE.finditer(text):
        start, end = match.group(1), match.group(2)
        timestamps.update((start, end))
        before = text[max(0, match.start() - 180):match.start()].strip().splitlines()
        after = text[match.end():match.end() + 700].strip().splitlines()
        label = next((line.strip() for line in reversed(before) if line.strip()), "Screenplay beat")
        content = "\n".join(line.strip() for line in after if line.strip())
        blocks.append({"start": start, "end": end, "label": label[-160:], "content": content[:1200]})
    return {
        "filename": filename,
        "episode": episode_match.group(1).strip() if episode_match else filename,
        "logline": logline_match.group(1).strip() if logline_match else "",
        "timestamps": sorted(timestamps, key=timestamp_seconds),
        "blocks": blocks,
    }
