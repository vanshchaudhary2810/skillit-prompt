"""Load prompt files from /prompts and fill in their {variables}.

Prompt files are the single source of truth: the app and the experiment runner read them,
so what is in the repository is exactly what was sent to the model.
"""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

# temperature None = model default
SETTINGS = {
    "v1": {"temperature": None, "json_mode": False},
    "v2": {"temperature": None, "json_mode": False},
    "v3": {"temperature": 0.2, "json_mode": True},
    "v4": {"temperature": 0.2, "json_mode": True},
}
VERSION_DIRS = {"v1": "v1", "v2": "v2", "v3": "v3", "v4": "final"}
FINAL_VERSION = "v4"


def load_prompt(version: str, name: str) -> dict:
    folder = PROMPTS_DIR / VERSION_DIRS[version]
    matches = sorted(folder.glob(f"{name}*.txt"))
    if not matches:
        raise FileNotFoundError(f"No prompt {name} in {folder}")
    text = matches[0].read_text(encoding="utf-8")
    system = text.split("### SYSTEM", 1)[1].split("### USER", 1)[0].strip()
    user = text.split("### USER", 1)[1].strip()
    return {"file": str(matches[0].relative_to(PROMPTS_DIR.parent)), "system": system, "user": user}


def render(template: str, variables: dict) -> str:
    """Replace only known {name} placeholders, so JSON braces in examples stay untouched."""
    out = template
    for key, value in variables.items():
        out = out.replace("{" + key + "}", str(value))
    return out
