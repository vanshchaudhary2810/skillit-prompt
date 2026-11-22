"""The Skill-it prompt workflow.

v1  = one baseline prompt (Milestone 1), plain text output
v2  = 4-step prompt chain, JSON asked in text, no grounding, default temperature
v3  = 4-step chain: role + rules + 1 example per prompt, JSON mode, temperature 0.2,
      retrieval of role profiles (P2) and free resources (P4), early stop on invalid input / unknown role
v4  = FINAL: as v3, but P3 writes out the readiness working (one row per must-have skill) before the score
"""
from __future__ import annotations

import json
import re

from . import kb
from .llm import GeminiClient
from .prompts import SETTINGS, load_prompt, render

STEP_NAMES = {
    "P0": "Baseline mentor prompt",
    "P1": "Skill Normaliser",
    "P2": "Role Requirements",
    "P3": "Gap Analyser",
    "P4": "Plan Builder",
}


# ---------------------------------------------------------------- helpers
def parse_json(raw: str) -> tuple[dict | None, bool, bool]:
    """Return (parsed, strict_ok, lenient_ok). Lenient = after removing ``` fences / extra text."""
    try:
        return json.loads(raw), True, True
    except Exception:
        pass
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1]), False, True
        except Exception:
            pass
    return None, False, False


def _call(client: GeminiClient, version: str, pid: str, variables: dict) -> dict:
    p = load_prompt(version, pid)
    system = render(p["system"], variables)
    user = render(p["user"], variables)
    s = SETTINGS[version]
    res = client.generate(system, user, temperature=s["temperature"], json_mode=s["json_mode"])
    step = {"id": pid, "name": STEP_NAMES[pid], "prompt_file": p["file"], "system": system, "user": user,
            "raw": res["text"], "model": res["model"], "latency_s": res["latency_s"]}
    if pid != "P0":
        parsed, strict_ok, lenient_ok = parse_json(res["text"])
        step.update(parsed=parsed, json_strict=strict_ok, json_ok=lenient_ok)
    return step


def week_hours(week: dict) -> float:
    """Hours actually planned in a v3 week (items + practice tasks)."""
    total = 0.0
    for it in week.get("items", []) or []:
        total += float(it.get("hours", 0) or 0)
    for t in week.get("practice_tasks", []) or []:
        if isinstance(t, dict):
            total += float(t.get("hours", 0) or 0)
    return round(total, 2)


# ---------------------------------------------------------------- v1
def run_v1(inputs: dict, client: GeminiClient) -> dict:
    step = _call(client, "v1", "P0", inputs)
    return {"version": "v1", "inputs": inputs, "steps": [step], "status": "ok", "final_text": step["raw"],
            "model": step["model"]}


# ---------------------------------------------------------------- v2
def run_v2(inputs: dict, client: GeminiClient) -> dict:
    out = {"version": "v2", "inputs": inputs, "steps": [], "status": "ok"}
    s1 = _call(client, "v2", "P1", {"student_skills": inputs["student_skills"]})
    out["steps"].append(s1)
    if not s1["json_ok"]:
        return _fail(out, "P1 output was not valid JSON")
    s2 = _call(client, "v2", "P2", {"target_role": inputs["target_role"]})
    out["steps"].append(s2)
    if not s2["json_ok"]:
        return _fail(out, "P2 output was not valid JSON")
    s3 = _call(client, "v2", "P3", {"student_profile": json.dumps(s1["parsed"]),
                                    "role_requirements": json.dumps(s2["parsed"])})
    out["steps"].append(s3)
    if not s3["json_ok"]:
        return _fail(out, "P3 output was not valid JSON")
    s4 = _call(client, "v2", "P4", {"gaps": json.dumps(s3["parsed"].get("gaps", s3["parsed"])),
                                    "weekly_hours": inputs["weekly_hours"], "num_weeks": inputs["num_weeks"]})
    out["steps"].append(s4)
    if not s4["json_ok"]:
        return _fail(out, "P4 output was not valid JSON")
    out["final"] = {"profile": s1["parsed"], "requirements": s2["parsed"], "gaps": s3["parsed"],
                    "plan": s4["parsed"]}
    out["model"] = s4["model"]
    return out


# ---------------------------------------------------------------- v3 (final)
def run_v3(inputs: dict, client: GeminiClient, on_step=None, version: str = "v3") -> dict:
    """Final chain. on_step(step_dict) is called after each step (used by the Streamlit UI)."""
    out = {"version": version, "inputs": inputs, "steps": [], "retrieval": {}, "status": "ok"}

    def add(step):
        out["steps"].append(step)
        out["model"] = step["model"]
        if on_step:
            on_step(step)

    # P1 - normalise skills
    s1 = _call(client, version, "P1", {"student_skills": inputs["student_skills"],
                                    "skill_vocabulary": kb.skill_vocabulary_text()})
    add(s1)
    if not s1["json_ok"]:
        return _fail(out, "P1 output was not valid JSON")
    p1 = s1["parsed"]
    canon = kb.canonical_skill_names()
    dropped = [sk for sk in p1.get("skills", []) if sk.get("name") not in canon]
    p1["skills"] = [sk for sk in p1.get("skills", []) if sk.get("name") in canon]  # code guardrail
    out["guard_dropped_noncanonical"] = dropped
    if p1.get("status") == "invalid_input" or not p1["skills"]:
        out["status"] = "invalid_input"
        out["message"] = p1.get("message") or "Please list at least one real skill."
        return out

    # P2 - role requirements, grounded on retrieved role profiles
    candidates = kb.retrieve_roles(inputs["target_role"], k=3)
    out["retrieval"]["roles"] = [{"name": c["name"], "match_score": c["match_score"]} for c in candidates]
    s2 = _call(client, version, "P2", {"target_role": inputs["target_role"],
                                    "candidate_roles": json.dumps(candidates, indent=1),
                                    "all_role_names": ", ".join(kb.all_role_names())})
    add(s2)
    if not s2["json_ok"]:
        return _fail(out, "P2 output was not valid JSON")
    p2 = s2["parsed"]
    if p2.get("status") == "unknown_role":
        out["status"] = "unknown_role"
        out["message"] = p2.get("message", "")
        out["suggested_roles"] = p2.get("suggested_roles", [])
        return out

    # P3 - gap analysis
    req_skills = [r["skill"] for r in p2.get("must_have", []) + p2.get("good_to_have", [])]
    s3 = _call(client, version, "P3", {
        "student_profile": json.dumps({"skills": p1["skills"]}, indent=1),
        "role_requirements": json.dumps({k: p2.get(k, []) for k in ("matched_role", "must_have", "good_to_have")}, indent=1),
        "effort_table": json.dumps(kb.effort_table(req_skills + [a for r in p2.get("must_have", []) for a in r.get("alternatives", []) or []]))})
    add(s3)
    if not s3["json_ok"]:
        return _fail(out, "P3 output was not valid JSON")
    p3 = s3["parsed"]
    gaps = p3.get("gaps", [])
    if not gaps:
        out["status"] = "no_gaps"
        out["final"] = {"profile": p1, "requirements": p2, "gaps": p3, "plan": None}
        return out

    # P4 - plan, grounded on retrieved resources
    gap_skills = [g["skill"] for g in gaps]
    alt = {r["skill"]: r.get("alternatives", []) or [] for r in p2.get("must_have", [])}
    retrieve_for = gap_skills + [a for g in gap_skills for a in alt.get(g, [])]
    resources = kb.retrieve_resources(retrieve_for)
    out["retrieval"]["resource_ids"] = [r["id"] for r in resources]
    res_for_prompt = [{k: r[k] for k in ("id", "title", "type", "skills", "level", "hours")} for r in resources]
    s4 = _call(client, version, "P4", {"gaps": json.dumps(gaps, indent=1),
                                    "weekly_hours": inputs["weekly_hours"], "num_weeks": inputs["num_weeks"],
                                    "resources": json.dumps(res_for_prompt, indent=1)})
    add(s4)
    if not s4["json_ok"]:
        return _fail(out, "P4 output was not valid JSON")
    p4 = s4["parsed"]
    if p4.get("status") == "insufficient_time":
        out["status"] = "insufficient_time"
        out["message"] = p4.get("notes") or p4.get("message", "")
    out["final"] = {"profile": p1, "requirements": p2, "gaps": p3, "plan": p4}
    return out


def _fail(out: dict, msg: str) -> dict:
    out["status"] = "error"
    out["error"] = msg
    return out


def run(version: str, inputs: dict, client: GeminiClient, on_step=None) -> dict:
    if version == "v1":
        return run_v1(inputs, client)
    if version == "v2":
        return run_v2(inputs, client)
    return run_v3(inputs, client, on_step=on_step, version=version)
