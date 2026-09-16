"""Loads versioned prompt text files from the top-level prompts/ directory.

Prompts are plain text, not f-strings scattered through the loop or the LLM
adapter. To change a prompt, add a new versioned file (e.g. system_v2.txt)
and update the one call site that names it - the old version stays on disk.
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(name: str) -> str:
    """Reads prompts/<name>.txt and returns its stripped contents."""
    path = _PROMPTS_DIR / f"{name}.txt"
    return path.read_text().strip()
