import asyncio
import json
import logging
import os

import config

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()


def _read_notes_sync() -> list[str]:
    path = config.NOTES_FILE_PATH
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(n) for n in data]
    except Exception as exc:
        logger.error("Failed to read notes file: %s", exc)
    return []


def _write_notes_sync(notes_list: list[str]) -> None:
    path = config.NOTES_FILE_PATH
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(notes_list, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


async def load_notes() -> list[str]:
    """Return all stored feedback notes, oldest first."""
    return await asyncio.to_thread(_read_notes_sync)


async def add_note(note: str) -> None:
    """Append a new feedback note, keeping only the most recent MAX_FEEDBACK_NOTES."""
    note = note.strip()
    if not note:
        return
    async with _lock:
        notes_list = await asyncio.to_thread(_read_notes_sync)
        notes_list.append(note)
        notes_list = notes_list[-config.MAX_FEEDBACK_NOTES:]
        await asyncio.to_thread(_write_notes_sync, notes_list)


async def notes_block() -> str:
    """
    Formatted block for injecting learned preferences into generation system prompts.
    Returns an empty string if there are no notes yet.
    """
    notes_list = await load_notes()
    if not notes_list:
        return ""
    joined = "\n".join(f"- {n}" for n in notes_list)
    return (
        "\n\nLEARNED PREFERENCES FROM PAST USER FEEDBACK "
        "(recent notes carry more weight; use judgment, don't force all of them into every prompt):\n"
        f"{joined}"
    )
