"""Automatic checks used for the test table and the prompt iteration log.

Every check is rule-based (no LLM-as-judge), so the numbers can be reproduced.
"""
from __future__ import annotations

import re

from . import kb
from .chain import week_hours

URL_RE = re.compile(r"https?://[^\s)\]>\"'*,]+")


HOUR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|to|–)?\s*(?:\d+(?:\.\d+)?)?\s*(?:hrs?|hours?|h)\b", re.I)


def _v1_week_hours(text: str) -> list[float]:
    """Best-effort hours per week from free text: split at 'Week N' headings; use a stated total if
    there is one, otherwise add up the hours mentioned for that week."""
    parts = re.split(r"(?i)\bweek\s*\d+\b", text)
    out = []
    for chunk in parts[1:]:
        chunk = re.split(r"(?i)\n#+\s|\n\*\*[A-Z][^*\n]{0,40}\*\*\s*\n", chunk)[0]  # stop at next section
        total = re.search(r"(?i)(?:total|time)[^\n\d]{0,25}(\d+(?:\.\d+)?)\s*(?:hrs?|hours?|h)\b", chunk)
        head = HOUR_RE.search(chunk[:80])
        if total:
            out.append(float(total.group(1)))
        elif head and len(HOUR_RE.findall(chunk)) == 1:
            out.append(float(head.group(1)))
        else:
            vals = [float(h) for h in HOUR_RE.findall(chunk)]
            if vals:
                out.append(sum(vals))
    return out


def _skill_match(gap: str, wanted: str) -> bool:
    """Lenient name match so non-canonical names ('Microsoft Excel', 'Advanced SQL') still count."""
    g, w = gap.lower(), wanted.lower()
    return w == g or re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", g) is not None


def _student_levels(result: dict) -> dict[str, int]:
    for st in result.get("steps", []):
        if st["id"] == "P1" and st.get("parsed"):
            return {s.get("name", ""): kb.level_index(s.get("level")) for s in st["parsed"].get("skills", [])
                    if isinstance(s, dict)}
    return {}


def _readiness(profile_levels: dict, must_have: list[dict]) -> int | None:
    total = sum(float(r.get("weight", 0) or 0) for r in must_have)
    if not total:
        return None
    got = 0.0
    for r in must_have:
        need = kb.level_index(r.get("required_level"))
        names = [r.get("skill")] + list(r.get("alternatives", []) or [])
        have = max([profile_levels.get(n, 0) for n in names] + [0])
        if have >= need:
            got += float(r.get("weight", 0))
        elif have > 0:
            got += float(r.get("weight", 0)) / 2
    return round(100 * got / total)


def metrics(result: dict) -> dict:
    v = result["version"]
    budget = float(result["inputs"]["weekly_hours"])
    n_weeks = int(result["inputs"]["num_weeks"])
    m: dict = {"version": v, "status": result.get("status"), "error": result.get("error")}

    if v == "v1":
        text = result.get("final_text", "")
        m["json_ok"] = False
        m["has_plan"] = bool(re.search(r"week\s*1\b", text, re.I))
        urls = [u.rstrip("/.") for u in URL_RE.findall(text)]
        m["resources_total"] = len(urls)
        m["resources_grounded"] = sum(1 for u in urls if u in kb.kb_urls())
        hours = _v1_week_hours(text)
        m["week_hours"] = hours
        m["hours_ok"] = (all(h <= budget for h in hours) if hours else None)
        return m

    steps = result.get("steps", [])
    m["json_ok"] = bool(steps) and all(s.get("json_ok") for s in steps)
    m["json_strict"] = bool(steps) and all(s.get("json_strict") for s in steps)
    final = result.get("final") or {}
    plan = final.get("plan") or {}
    weeks = plan.get("weeks") if isinstance(plan, dict) else None
    m["has_plan"] = bool(weeks)
    student = _student_levels(result)

    # gaps / false gaps
    gaps_obj = final.get("gaps") or {}
    gaps = gaps_obj.get("gaps", []) if isinstance(gaps_obj, dict) else (gaps_obj if isinstance(gaps_obj, list) else [])
    m["gap_skills"] = [g.get("skill") for g in gaps if isinstance(g, dict)]
    false_gaps = []
    for g in gaps:
        if not isinstance(g, dict):
            continue
        if student.get(g.get("skill"), 0) >= kb.level_index(g.get("required_level")) and student.get(g.get("skill"), 0) > 0:
            false_gaps.append(g.get("skill"))
    m["false_gaps"] = false_gaps

    if weeks:
        m["weeks_ok"] = len(weeks) == n_weeks
        if v in ("v3", "v4"):
            hrs = [week_hours(w) for w in weeks]
            m["total_mismatch"] = sum(1 for w, h in zip(weeks, hrs) if abs(float(w.get("total_hours", 0) or 0) - h) > 0.01)
            allowed = set(result.get("retrieval", {}).get("resource_ids", []))
            ids = [it.get("resource_id") for w in weeks for it in (w.get("items") or [])]
            m["resources_total"] = len(ids)
            m["resources_grounded"] = sum(1 for i in ids if i in allowed)
        else:
            hrs = []
            for w in weeks:
                h = w.get("total_hours", w.get("hours"))
                try:
                    hrs.append(float(h))
                except (TypeError, ValueError):
                    hrs.append(None)
            urls = [str(r.get("url", "")).rstrip("/.") for w in weeks for r in (w.get("resources") or []) if isinstance(r, dict)]
            m["resources_total"] = len(urls)
            m["resources_grounded"] = sum(1 for u in urls if u in kb.kb_urls())
        m["week_hours"] = hrs
        m["hours_ok"] = all(h is not None and h <= budget + 1e-9 for h in hrs)
        m["max_week_hours"] = max([h for h in hrs if h is not None], default=None)
        m["deferred_gaps"] = plan.get("deferred_gaps", [])

    if v in ("v3", "v4") and final.get("requirements"):
        expected = _readiness(student, final["requirements"].get("must_have", []))
        got = gaps_obj.get("readiness_score") if isinstance(gaps_obj, dict) else None
        m["readiness_expected"], m["readiness_model"] = expected, got
        m["readiness_ok"] = (expected is not None and isinstance(got, (int, float)) and abs(got - expected) <= 5)
    return m


def evaluate_test(test: dict, result: dict, m: dict) -> tuple[bool, list[str]]:
    """Return (passed, reasons_for_failure) using the test's expectations."""
    exp = test.get("expect", {})
    v = result["version"]
    reasons = []
    want_status = exp.get("status", "ok")

    if v == "v1":
        if want_status != "ok":
            if m["has_plan"]:
                reasons.append(f"made a plan instead of '{want_status}'")
        else:
            if not m["has_plan"]:
                reasons.append("no week plan")
            if m["hours_ok"] is False:
                reasons.append(f"week hours over limit {m['week_hours']}")
            if m["hours_ok"] is None:
                reasons.append("hours per week not stated")
            text = result.get("final_text", "").lower()
            for group in exp.get("gaps_include", []):
                if not any(s.lower() in text for s in group):
                    reasons.append(f"missing gap {group[0]}")
        reasons.append("output is not machine-readable (plain text)")
        return (len(reasons) == 0), reasons

    status = result.get("status")
    if v == "v2":
        status = "ok" if status != "error" else "error"
    if status == "error":
        return False, [result.get("error", "error")]
    if status != want_status:
        reasons.append(f"status '{status}' but expected '{want_status}'")
        return False, reasons

    if want_status == "ok":
        if not m.get("json_ok"):
            reasons.append("invalid JSON")
        if m.get("has_plan"):
            if not m.get("weeks_ok"):
                reasons.append("wrong number of weeks")
            if not m.get("hours_ok"):
                reasons.append(f"week over {test['input']['weekly_hours']} h limit ({m.get('max_week_hours')} h)")
            if m.get("resources_total", 0) and m.get("resources_grounded", 0) < m.get("resources_total", 0):
                reasons.append(f"{m['resources_total'] - m['resources_grounded']} resource(s) not from the curated list")
        if m.get("false_gaps"):
            reasons.append(f"false gap(s): {', '.join(m['false_gaps'])}")
        gap_names = [g for g in m.get("gap_skills", []) if g]
        for group in exp.get("gaps_include", []):
            if not any(_skill_match(g, s) for g in gap_names for s in group):
                reasons.append(f"missing gap {'/'.join(group)}")
        for s in exp.get("gaps_exclude", []):
            if any(g.lower() == s.lower() for g in gap_names):
                reasons.append(f"{s} wrongly listed as gap")
        if "max_must_have_gaps" in exp:
            gaps = (result.get("final", {}).get("gaps") or {})
            gaps = gaps.get("gaps", []) if isinstance(gaps, dict) else gaps
            mh = [g for g in gaps if isinstance(g, dict) and g.get("type", "must_have") == "must_have"]
            if len(mh) > exp["max_must_have_gaps"]:
                reasons.append(f"{len(mh)} must-have gaps (expected <= {exp['max_must_have_gaps']})")
        if exp.get("deferred_nonempty") and not m.get("deferred_gaps"):
            reasons.append("no deferred gaps although time is too short")
        if v in ("v3", "v4") and m.get("readiness_ok") is False:
            reasons.append(f"readiness {m.get('readiness_model')} vs rule {m.get('readiness_expected')}")
    if exp.get("p1_maps"):
        names = set(_student_levels(result).keys())
        for raw, canon in exp["p1_maps"].items():
            if canon not in names:
                reasons.append(f"'{raw}' not mapped to {canon}")
    if exp.get("matched_role_in") and v in ("v3", "v4"):
        got = (result.get("final", {}).get("requirements") or {}).get("matched_role", "")
        if got not in exp["matched_role_in"]:
            reasons.append(f"matched role '{got}'")
    if want_status == "unknown_role" and v in ("v3", "v4") and not result.get("suggested_roles"):
        reasons.append("no role suggestions")
    return (len(reasons) == 0), reasons


def short_actual(result: dict, m: dict) -> str:
    v = result["version"]
    if result.get("status") == "error":
        return f"Error: {result.get('error')}"
    if v in ("v3", "v4") and result.get("status") in ("invalid_input", "unknown_role", "insufficient_time"):
        extra = ""
        if result.get("suggested_roles"):
            extra = "; suggests " + ", ".join(result["suggested_roles"][:3])
        return f"Stopped: {result['status']}{extra}"
    if v == "v1":
        return (f"Plain text; plan={'yes' if m['has_plan'] else 'no'}; "
                f"{m['resources_total']} links ({m['resources_grounded']} in curated list)")
    parts = []
    if m.get("gap_skills"):
        parts.append(f"{len(m['gap_skills'])} gaps ({', '.join(m['gap_skills'][:4])}{'...' if len(m['gap_skills']) > 4 else ''})")
    if m.get("has_plan"):
        parts.append(f"{len(m.get('week_hours', []))}-wk plan, max {m.get('max_week_hours')} h/wk")
        parts.append(f"{m.get('resources_grounded', 0)}/{m.get('resources_total', 0)} resources curated")
    if m.get("deferred_gaps"):
        parts.append(f"deferred: {', '.join(m['deferred_gaps'][:3])}")
    if v in ("v3", "v4") and m.get("readiness_model") is not None:
        parts.append(f"readiness {m['readiness_model']}")
    return "; ".join(parts) or result.get("status", "")
