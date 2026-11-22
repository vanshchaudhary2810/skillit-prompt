"""Run every prompt version on every test input, check the outputs automatically and save everything.

Usage (from the repository root):
    export GEMINI_API_KEY="your key"          # Windows PowerShell:  $env:GEMINI_API_KEY="your key"
    python code/run_experiments.py            # all versions, all tests (~150 API calls, ~15 min on free tier)
    python code/run_experiments.py --versions v3 --tests T01,T07

Outputs:
    test-data/outputs/<version>/<test>.json   full trace: rendered prompts, raw model output, parsed JSON
    test-data/results.json / results.csv      metrics + pass/fail per version and test
    test-data/summary.md                      version comparison used in the iteration log
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skillit import chain, validate  # noqa: E402
from skillit.llm import GeminiClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TD = ROOT / "test-data"


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="v1,v2,v3,v4")
    ap.add_argument("--tests", default="all")
    ap.add_argument("--model", default=None)
    ap.add_argument("--interval", type=float, default=6.0, help="seconds between API calls (free tier ~10/min)")
    ap.add_argument("--repeats", type=int, default=3, help="extra runs of T01 for the consistency check (v2, v3, v4)")
    ap.add_argument("--force", action="store_true", help="re-run even if an output file already exists")
    args = ap.parse_args()

    tests = json.loads((TD / "test_inputs.json").read_text(encoding="utf-8"))["tests"]
    if args.tests != "all":
        wanted = set(args.tests.split(","))
        tests = [t for t in tests if t["id"] in wanted]
    versions = args.versions.split(",")
    client = GeminiClient(model=args.model, min_interval=args.interval)

    rows = []
    for v in versions:
        (TD / "outputs" / v).mkdir(parents=True, exist_ok=True)
        for t in tests:
            path = TD / "outputs" / v / f"{t['id']}.json"
            if path.exists() and not args.force:
                result = json.loads(path.read_text(encoding="utf-8"))
                print(f"[{v} {t['id']}] cached")
            else:
                print(f"[{v} {t['id']}] running ...", flush=True)
                t0 = time.time()
                try:
                    result = chain.run(v, dict(t["input"]), client)
                except Exception as e:  # keep going, record the failure honestly
                    result = {"version": v, "inputs": t["input"], "steps": [], "status": "error", "error": str(e)}
                result["run_at"] = datetime.now().isoformat(timespec="seconds")
                result["wall_time_s"] = round(time.time() - t0, 1)
                path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            m = validate.metrics(result)
            passed, reasons = validate.evaluate_test(t, result, m)
            rows.append({"version": v, "test": t["id"], "type": t["type"], "title": t["title"],
                         "input_short": f"{t['input']['student_skills'][:45]} | {t['input']['target_role']} | "
                                        f"{t['input']['weekly_hours']} h x {t['input']['num_weeks']} wk",
                         "expected": t["expected_text"], "actual": validate.short_actual(result, m),
                         "pass": passed, "reasons": "; ".join(reasons), "model": result.get("model", ""),
                         "metrics": m})
            print(f"    -> {'PASS' if passed else 'FAIL'} {'; '.join(reasons)}")

    # consistency check: same input several times, compare the gap lists
    consistency = {}
    t01 = next((t for t in json.loads((TD / "test_inputs.json").read_text())["tests"] if t["id"] == "T01"), None)
    for v in [x for x in versions if x in ("v2", "v3", "v4")]:
        if not args.repeats or t01 is None:
            break
        runs = []
        base = TD / "outputs" / v / "T01.json"
        if base.exists():
            runs.append(json.loads(base.read_text()))
        for i in range(1, args.repeats):
            p = TD / "outputs" / v / f"T01_repeat{i}.json"
            if p.exists() and not args.force:
                runs.append(json.loads(p.read_text()))
                continue
            print(f"[{v} T01 repeat {i}] running ...", flush=True)
            try:
                r = chain.run(v, dict(t01["input"]), client)
            except Exception as e:
                r = {"version": v, "inputs": t01["input"], "steps": [], "status": "error", "error": str(e)}
            p.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
            runs.append(r)
        gap_sets = [set(validate.metrics(r).get("gap_skills", [])) for r in runs]
        pairs = [(i, j) for i in range(len(gap_sets)) for j in range(i + 1, len(gap_sets))]
        consistency[v] = {"runs": len(runs), "gap_sets": [sorted(g) for g in gap_sets],
                          "mean_jaccard": round(sum(jaccard(gap_sets[i], gap_sets[j]) for i, j in pairs) / max(1, len(pairs)), 2)}

    # summary per version
    summary = {}
    for v in versions:
        vr = [r for r in rows if r["version"] == v]
        ms = [r["metrics"] for r in vr]
        plan_ms = [m for m in ms if m.get("has_plan")]
        res_total = sum(m.get("resources_total", 0) or 0 for m in ms)
        res_ground = sum(m.get("resources_grounded", 0) or 0 for m in ms)
        summary[v] = {
            "tests": len(vr),
            "passed": sum(r["pass"] for r in vr),
            "json_valid_runs": sum(1 for m in ms if m.get("json_ok")),
            "json_strict_runs": sum(1 for m in ms if m.get("json_strict")),
            "plans_made": len(plan_ms),
            "plans_within_hours": sum(1 for m in plan_ms if m.get("hours_ok")),
            "plans_hours_unknown": sum(1 for m in plan_ms if m.get("hours_ok") is None),
            "resources_total": res_total,
            "resources_from_curated_list": res_ground,
            "runs_with_false_gaps": sum(1 for m in ms if m.get("false_gaps")),
            "edge_invalid_passed": sum(r["pass"] for r in vr if r["type"] != "Normal"),
            "edge_invalid_total": sum(1 for r in vr if r["type"] != "Normal"),
            "readiness_rule_ok": sum(1 for m in ms if m.get("readiness_ok")) if v in ("v3", "v4") else None,
            "consistency_T01": consistency.get(v),
            "model": ", ".join(sorted({r["model"] for r in vr if r["model"]})),
        }

    (TD / "results.json").write_text(json.dumps({"generated": datetime.now().isoformat(timespec="seconds"),
                                                 "summary": summary, "rows": rows}, indent=2, ensure_ascii=False),
                                     encoding="utf-8")
    with open(TD / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["version", "test", "type", "input", "expected", "actual", "pass", "reasons"])
        for r in rows:
            w.writerow([r["version"], r["test"], r["type"], r["input_short"], r["expected"], r["actual"],
                        "Pass" if r["pass"] else "Fail", r["reasons"]])
    lines = ["# Experiment summary", "", f"Generated {datetime.now():%Y-%m-%d %H:%M}", "",
             "| Metric | " + " | ".join(versions) + " |", "|---|" + "---|" * len(versions)]
    for key in ["tests", "passed", "json_valid_runs", "json_strict_runs", "plans_made", "plans_within_hours",
                "resources_total", "resources_from_curated_list", "runs_with_false_gaps", "edge_invalid_passed",
                "readiness_rule_ok", "model"]:
        lines.append(f"| {key} | " + " | ".join(str(summary[v].get(key)) for v in versions) + " |")
    for v, c in consistency.items():
        lines.append(f"\nConsistency {v} (T01 x{c['runs']}): mean Jaccard of gap lists = {c['mean_jaccard']}")
    (TD / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nTotal API calls this session: {client.calls}. Model: {client.model}")


if __name__ == "__main__":
    main()
