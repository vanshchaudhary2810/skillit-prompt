"""Knowledge base loading and retrieval (the grounding / RAG part of Skill-it).

Retrieval is deliberately simple and explainable:
  * roles      -> fuzzy match of the typed role against role names + aliases (top-k profiles)
  * resources  -> resources whose skill tags overlap the gap skills (and their alternatives)
The retrieved text is injected into prompts P2 and P4 so the model can only use known data.
"""
from __future__ import annotations

import difflib
import json
import re
from functools import lru_cache
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent / "kb"
LEVELS = ["none", "beginner", "intermediate", "advanced"]


def level_index(level: str | None) -> int:
    level = (level or "none").strip().lower()
    return LEVELS.index(level) if level in LEVELS else 0


@lru_cache
def load_skills() -> list[dict]:
    return json.loads((KB_DIR / "skills.json").read_text(encoding="utf-8"))["skills"]


@lru_cache
def load_roles() -> list[dict]:
    return json.loads((KB_DIR / "roles.json").read_text(encoding="utf-8"))["roles"]


@lru_cache
def load_resources() -> list[dict]:
    return json.loads((KB_DIR / "resources.json").read_text(encoding="utf-8"))["resources"]


def canonical_skill_names() -> set[str]:
    return {s["name"] for s in load_skills()}


def skill_vocabulary_text() -> str:
    lines = []
    for s in load_skills():
        alias = ", ".join(s["aliases"]) if s["aliases"] else "-"
        lines.append(f"{s['name']}: {alias}")
    return "\n".join(lines)


def effort_table(skills: list[str] | None = None) -> dict[str, int]:
    table = {s["name"]: s["hours_per_level"] for s in load_skills()}
    if skills:
        return {k: v for k, v in table.items() if k in set(skills)}
    return table


def all_role_names() -> list[str]:
    return [r["name"] for r in load_roles()]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9+/ ]", " ", (text or "").lower()).strip()


def retrieve_roles(typed_role: str, k: int = 3) -> list[dict]:
    """Return the top-k role profiles with a match score (0-1)."""
    q = _norm(typed_role)
    q_tokens = set(q.split())
    scored = []
    for role in load_roles():
        names = [role["name"]] + role.get("aliases", [])
        best = 0.0
        for n in names:
            n_norm = _norm(n)
            ratio = difflib.SequenceMatcher(None, q, n_norm).ratio()
            n_tokens = set(n_norm.split())
            overlap = len(q_tokens & n_tokens) / max(1, len(n_tokens))
            exact = 1.0 if n_norm and (n_norm == q or f" {n_norm} " in f" {q} ") else 0.0
            best = max(best, ratio, overlap * 0.9, exact)
        scored.append((round(best, 3), role))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, role in scored[:k]:
        r = {key: role[key] for key in ("name", "must_have", "good_to_have")}
        r["match_score"] = score
        out.append(r)
    return out


def role_profile(name: str) -> dict | None:
    for r in load_roles():
        if r["name"].lower() == (name or "").lower():
            return r
    return None


def retrieve_resources(gap_skills: list[str], per_skill: int = 4) -> list[dict]:
    """Return resources tagged with any gap skill, at most `per_skill` per skill, no duplicates."""
    chosen: dict[str, dict] = {}
    for skill in gap_skills:
        matches = [r for r in load_resources() if skill in r["skills"]]
        # prefer resources focused on fewer skills (more specific) and shorter ones
        matches.sort(key=lambda r: (len(r["skills"]), r["hours"]))
        for r in matches[:per_skill]:
            chosen[r["id"]] = r
    return sorted(chosen.values(), key=lambda r: r["id"])


def resource_by_id(rid: str) -> dict | None:
    for r in load_resources():
        if r["id"] == rid:
            return r
    return None


def kb_urls() -> set[str]:
    return {r["url"].rstrip("/") for r in load_resources() if r["url"]}
