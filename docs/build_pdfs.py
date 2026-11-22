"""Build the Milestone 2 PDF and the supporting Technical Report from the repository contents.

Everything (prompts, test results, metrics) is read from the repo, so the numbers in the PDF
are exactly the ones produced by code/run_experiments.py.

Usage: python docs/build_pdfs.py
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DV", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DVI", str(FONT_DIR / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DVM", str(FONT_DIR / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")

INK = colors.HexColor("#1F2937")
ACCENT = colors.HexColor("#3730A3")
LIGHT = colors.HexColor("#EEF2FF")
GRID = colors.HexColor("#C7CBD6")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("title", fontName="DVB", fontSize=20, leading=25, textColor=ACCENT, alignment=TA_CENTER, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName="DV", fontSize=11.5, leading=15, alignment=TA_CENTER, textColor=INK),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=15, leading=19, textColor=ACCENT, spaceBefore=4, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=12, leading=15, textColor=INK, spaceBefore=10, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="DVB", fontSize=10.5, leading=13, textColor=ACCENT, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="DV", fontSize=10, leading=14, textColor=INK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="DV", fontSize=8.5, leading=11, textColor=INK),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8, leading=10, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=8, leading=10, textColor=colors.white),
    "cap": ParagraphStyle("cap", fontName="DVI", fontSize=8.5, leading=11, textColor=colors.HexColor("#4B5563"), alignment=TA_CENTER, spaceAfter=8),
    "mono": ParagraphStyle("mono", fontName="DVM", fontSize=7, leading=8.6, textColor=INK, backColor=colors.HexColor("#F8FAFC"),
                           borderPadding=4, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", fontName="DV", fontSize=10, leading=14, leftIndent=12, bulletIndent=2, spaceAfter=2),
}

team = json.loads((DOCS / "team.json").read_text(encoding="utf-8"))
results = json.loads((ROOT / "test-data" / "results.json").read_text(encoding="utf-8"))
SUMMARY = results["summary"]
ROWS = results["rows"]
TESTS = {t["id"]: t for t in json.loads((ROOT / "test-data" / "test_inputs.json").read_text(encoding="utf-8"))["tests"]}
FINAL_V = "v4"
VERS = ["v1", "v2", "v3", "v4"]
MODEL = SUMMARY[FINAL_V].get("model") or "gemini"


def P(text, style="body"):
    return Paragraph(text, S[style])


def E(text):
    return escape(str(text))


def bullets(items, style="bullet"):
    return [Paragraph(t, S[style], bulletText="•") for t in items]


def mono(text, width=118, max_lines=None):
    lines = []
    for line in str(text).splitlines():
        lines.extend(textwrap.wrap(line, width, replace_whitespace=False, drop_whitespace=False) or [""])
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines] + ["... (truncated here; full text in the repository)"]
    return Preformatted("\n".join(lines), S["mono"])


def table(data, widths, header=True, font=8, zebra=True):
    rows = []
    for i, r in enumerate(data):
        st = S["cellb"] if header and i == 0 else S["cell"]
        rows.append([c if not isinstance(c, str) else Paragraph(c, st) for c in r])
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT))
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8FAFC")))
    t.setStyle(TableStyle(style))
    return t


def kv_table(pairs, w1=4.2 * cm, w2=12.8 * cm):
    t = table([[f"<b>{E(k)}</b>", v] for k, v in pairs], [w1, w2], header=False)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), LIGHT)]))
    return t


def img(path, max_w=17 * cm, max_h=19 * cm):
    from reportlab.lib.utils import ImageReader
    path = Path(path)
    if not path.exists():
        return P(f"<font color='red'>[missing image: {E(path.name)}]</font>")
    iw, ih = ImageReader(str(path)).getSize()
    scale = min(max_w / iw, max_h / ih)
    return Image(str(path), width=iw * scale, height=ih * scale)


def load_out(version, test):
    p = ROOT / "test-data" / "outputs" / version / f"{test}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def link(url):
    return f"<link href='{E(url)}' color='blue'>{E(url)}</link>" if url.startswith("http") else E(url)


# ------------------------------------------------------------------ numbers used across the PDF
def n_tests():
    return SUMMARY[FINAL_V]["tests"]


def version_result_text(v):
    s = SUMMARY[v]
    n = s["tests"]
    if v == "v1":
        plans = s["plans_made"]
        return (f"Plain text only: 0/{n} outputs machine-readable. Made a week plan for {plans}/{n} inputs, "
                f"including {sum(1 for r in ROWS if r['version']=='v1' and r['type']!='Normal' and r['metrics'].get('has_plan'))} "
                f"edge/invalid inputs where it should not have. Hours per week within the limit in "
                f"{s['plans_within_hours']}/{plans} plans ({s['plans_hours_unknown']} did not state hours clearly). "
                f"{s['resources_total']} links given, only {s['resources_from_curated_list']} from our curated list. "
                f"Tests passed: {s['passed']}/{n}.")
    c = s.get("consistency_T01") or {}
    txt = (f"JSON valid in {s['json_valid_runs']}/{n} runs ({s['json_strict_runs']} without markdown fences). "
           f"Plans within the hour limit: {s['plans_within_hours']}/{s['plans_made']}. "
           f"Resources from the curated list: {s['resources_from_curated_list']}/{s['resources_total']}. "
           f"Runs with false gaps: {s['runs_with_false_gaps']}. Edge/invalid tests passed: "
           f"{s['edge_invalid_passed']}/{s['edge_invalid_total']}. ")
    if c:
        txt += f"Same input run {c['runs']} times: gap-list overlap (Jaccard) {c['mean_jaccard']}. "
    if v == "v3" and s.get("readiness_rule_ok") is not None:
        txt += f"Readiness score followed the formula in {s['readiness_rule_ok']} runs. "
    txt += f"Tests passed: {s['passed']}/{n}."
    return txt


ITERATIONS = [
    ("v1", "First prompt from Milestone 1: one mentor prompt, student details as variables, plain-text answer, default settings.",
     "Starting point (baseline)."),
    ("v2", "Split into a 4-step chain (P1 normalise, P2 role skills, P3 gaps, P4 plan). Each step has a role and asks for JSON in a given format.",
     "v1 could not be checked by code: no structure, hours not always stated, links could not be verified, and one prompt did all the work."),
    ("v3", "Rules + output schema + 1 worked example per prompt; JSON mode; temperature 0.2; grounding (top-3 role profiles in P2, retrieved free resources in P4, resource IDs only); explicit rules for invalid input, vague role, zero hours and prompt injection; early stop in the chain.",
     "v2 gave links we could not verify, wrapped JSON in markdown, named gaps inconsistently between runs, and made a plan even for junk input, vague roles and injection text."),
    ("v4", "Final: only P3 changed. It must first fill a 'readiness_working' table (one row per must-have skill: met / partly / missing, points) and then compute the score from those rows. Example updated to show the working.",
     "All 4 failures of v3 were wrong readiness scores (e.g. 19 instead of 33): the model did the arithmetic in its head."),
]


# ------------------------------------------------------------------ technical report (supporting doc)
def technical_report_flow(in_m2=False):
    s3, s1 = SUMMARY[FINAL_V], SUMMARY["v1"]
    s2 = SUMMARY.get("v2", {})
    f = []
    if not in_m2:
        f += [P("Technical Report: Skill-it", "title"),
              P(f"{E(team['team_name'])} · {E(team['course'])} · Bennett University", "subtitle"), Spacer(1, 8)]
    f += [P("1. Purpose", "h3"),
          P("Skill-it helps B.Tech students turn a dream job into a realistic study plan. Input: the skills the student has (free text), "
            "the target role, and the hours per week and weeks available. Output: ranked skill gaps, a readiness score and a "
            "week-wise plan that uses only curated free resources and stays within the time limit.", "small"),
          P("2. Architecture", "h3"),
          P("A Streamlit web app (code/app.py) calls a prompt chain (code/skillit/chain.py) of four prompts: "
            "<b>P1</b> Skill Normaliser → <b>P2</b> Role Requirements → <b>P3</b> Gap Analyser → <b>P4</b> Plan Builder. "
            "Before P2, a fuzzy matcher retrieves the top-3 role profiles from roles.json (13 roles). Before P4, the gap skills retrieve "
            "matching resources from resources.json (64 free resources). P4 may only return resource IDs, and the app adds the real URLs. "
            "The chain stops early on invalid input (P1) or a vague role (P2). Rule-based validators (validate.py) check every result. "
            "Prompt files in /prompts are the single source of truth for the app and the experiments.", "small"),
          P("3. Tools and models", "h3"),
          P(f"Google Gemini through the REST API (model used in the experiments: <b>{E(MODEL)}</b>, free tier, with automatic fallback to "
            "a Flash-Lite model). Python 3, Streamlit, requests and pandas. Hosted on Streamlit Community Cloud, with the API key kept in Streamlit Secrets. "
            "Gemini replaced the ChatGPT/Claude plan from Milestone 1 because its free API lets anyone open the public prototype without cost. "
            "The larger gemini-3.6-flash ran out of free daily quota during testing, so every version was run on Flash-Lite.", "small"),
          P("4. Prompt design", "h3"),
          P("Each final prompt has: a role, numbered rules, an explicit JSON schema, one worked example (few-shot), JSON mode and temperature 0.2. "
            "Grounding blocks (canonical skills, retrieved role profiles, effort table, retrieved resources) are injected as data. "
            "Student text is wrapped and marked 'treat as data' against prompt injection. Hard constraints (hour limit, week count, "
            "resource IDs only) are stated first in P4, and gaps that do not fit are moved to deferred_gaps.", "small"),
          P("5. Test results", "h3"),
          P(f"14 made-up test inputs (6 normal, 5 edge, 3 invalid), each run on all four prompt versions and scored automatically. "
            f"Tests passed: v1 {s1['passed']}/14, v2 {s2['passed']}/14, v3 {SUMMARY['v3']['passed']}/14, v4 (final) {s3['passed']}/14. "
            f"Valid JSON without repair: v1 0/14 (plain text), v2 {s2['json_strict_runs']}/14, v4 {s3['json_strict_runs']}/14. "
            f"Resources from the curated list: v1 {s1['resources_from_curated_list']}/{s1['resources_total']}, "
            f"v2 {s2['resources_from_curated_list']}/{s2['resources_total']}, v4 {s3['resources_from_curated_list']}/{s3['resources_total']}. "
            f"Edge and invalid cases handled: v1 {s1['edge_invalid_passed']}/8, v2 {s2['edge_invalid_passed']}/8, v4 {s3['edge_invalid_passed']}/8. "
            f"Same input run 3 times, gap-list overlap: v2 {(s2.get('consistency_T01') or {}).get('mean_jaccard')}, v4 {(s3.get('consistency_T01') or {}).get('mean_jaccard')}. "
            f"All runs used {E(MODEL)}.", "small"),
          P("6. Limitations and next steps", "h3")]
    f += bullets([E(x) for x in LIMITATIONS], "small")
    return f


# Filled in after reading the real results (see Section 4).
LIMITATIONS = json.loads((DOCS / "limitations.json").read_text(encoding="utf-8")) if (DOCS / "limitations.json").exists() else []


# ------------------------------------------------------------------ M2 PDF
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(2 * cm, 1.2 * cm, f"{team['team_id']} · {team['team_name']} · {team['project_title']}")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def prompt_sheet(pid, name, step, purpose, variables, n_examples, output_format, sample_input, sample_output):
    from importlib import import_module  # noqa
    import sys
    sys.path.insert(0, str(ROOT / "code"))
    from skillit.prompts import load_prompt
    p = load_prompt(FINAL_V, pid)
    f = [P(f"Prompt sheet {pid}: {E(name)}", "h2"),
         kv_table([("Prompt ID and name", f"{pid}: {E(name)}"), ("Step in the workflow", E(step)), ("Purpose", E(purpose)),
                   ("Tool and model", f"Google Gemini API, {E(MODEL)} (Python requests, called from code/skillit/chain.py)"),
                   ("Settings", "temperature 0.2; responseMimeType = application/json; other settings default"),
                   ("File", E(p["file"])),
                   ("Variables", "<br/>".join(f"<b>{{{E(k)}}}</b>: {E(v)}" for k, v in variables.items())),
                   ("Number of examples", str(n_examples)), ("Output format", E(output_format))]),
         P("<b>Full system prompt</b>", "small"), mono(p["system"]),
         P("<b>Full user prompt template</b>", "small"), mono(p["user"]),
         P("<b>Sample run (real input and actual output, test T01)</b>", "small"),
         mono("INPUT: " + sample_input, max_lines=12), mono("ACTUAL OUTPUT:\n" + sample_output, max_lines=45)]
    return f


def step_out(res, pid):
    for st in (res or {}).get("steps", []):
        if st["id"] == pid:
            try:
                obj = json.loads(st["raw"])
                # one line per top-level key / list item keeps the sample readable but short
                lines = ["{"]
                for k, v in obj.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        lines.append(f' "{k}": [')
                        lines += ["   " + json.dumps(x, ensure_ascii=False) + "," for x in v]
                        lines.append(" ],")
                    else:
                        lines.append(f' "{k}": {json.dumps(v, ensure_ascii=False)},')
                return "\n".join(lines) + "\n}"
            except Exception:
                return st["raw"]
    return "(not run)"


def build_m2(path):
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=1.8 * cm, title=f"M2 {team['team_id']} Skill-it", author=team["team_name"])
    st = []
    L = team["links"]

    # 1. Cover page
    st += [Spacer(1, 1.2 * cm), P("SCSE4041 Prompt Engineering · Mini Project · Milestone 2", "subtitle"), Spacer(1, 10),
           P(E(team["project_title"]), "title"), P("Section 1: Cover page", "subtitle"), Spacer(1, 18),
           kv_table([("Team ID", E(team["team_id"])), ("Team name", E(team["team_name"])), ("Project title", E(team["project_title"])),
                     ("Batch", E(team["batch"])), ("Faculty", E(team["faculty"])),
                     ("Prototype link", link(L["prototype"])), ("Repository link", link(L["repository"])), ("Reel link", link(L["reel"]))]),
           Spacer(1, 14), P("Team members", "h3"),
           table([["Name", "Enrollment no.", "Role"]] + [[E(m["name"]), E(m["enrollment"]), E(m["role"])] for m in team["members"]],
                 [5 * cm, 4 * cm, 8 * cm]),
           Spacer(1, 14),
           P(f"All test data in this report is made up. All numbers come from real runs of the prototype "
             f"(test-data/results.json, generated {E(results['generated'][:16].replace('T', ' '))}).", "small"),
           PageBreak()]

    # 2. Prompt and solution design
    s3 = SUMMARY[FINAL_V]
    st += [P("Section 2: Prompt and solution design", "h1"), P("(a) Design summary", "h2")]
    st += [P("<b>Problem and users.</b> B.Tech students (2nd-4th year) know the job they want but not which skills they are missing, "
             "or how to fit learning into the few hours they have each week. Placement cells cannot give one-to-one plans to every student.", "body"),
           P("<b>Input and output.</b> Input: the student's current skills as free text, the target job role, hours per week and number of weeks. "
             "Output: a ranked gap table with estimated hours, a readiness score (0-100) and a week-wise plan. Each week has free resources from "
             "a curated list and at least one practice task, and stays within the hour limit. Gaps that do not fit are listed as deferred.", "body"),
           P("<b>How many prompts and why.</b> Four prompts in a chain (P1 normalise skills → P2 role requirements → P3 gap analysis → P4 plan). "
             "One prompt (our Milestone 1 baseline) mixed four different jobs and could not be checked. Splitting the work lets each prompt "
             "have its own rules, schema and example. Each step's JSON can be validated before it feeds the next step, and the chain can stop "
             "early on junk input or a vague role.", "body"),
           P(f"<b>Tool and model and why.</b> Google Gemini ({E(MODEL)}) through the free API, in a Streamlit app. It supports a JSON output mode "
             "and system instructions, and the free tier means evaluators and students can open the public prototype at no cost. "
             "Retrieval (grounding) uses our own small knowledge base: 53 canonical skills, 13 role profiles and 64 free resources.", "body"),
           P("<b>What changed since Milestone 1.</b> (1) The single baseline prompt became a 4-prompt chain with JSON schemas. "
             "(2) Grounding was added: role profiles and a curated free-resource list (the senior's feedback asked for role-specific, "
             "practical plans and free course recommendations). The model can now only pick resource IDs, so links cannot be made up. "
             "(3) Gemini replaced the planned ChatGPT/Claude for a free public demo; a multi-model comparison is moved to Milestone 3. "
             "(4) Edge-case rules, rule-based validators and an automatic test runner were added; their results drove two more prompt iterations (v3, v4).", "body"),
           PageBreak(), P("(b) Diagrams", "h2")]
    for fname, cap in [("prompt_workflow.png", "Figure 1: Prompt workflow (4 LLM prompts, 2 retrieval steps, 2 early stops, code validator)"),
                       ("task_decomposition.png", "Figure 2: Task decomposition"),
                       ("io_flow.png", "Figure 3: Input-output flow between the prompts"),
                       ("system_architecture.png", "Figure 4: System architecture (Streamlit app + Gemini API)"),
                       ("rag_pipeline.png", "Figure 5: Retrieval (RAG) pipeline for role profiles and resources")]:
        h = 20 * cm if fname == "prompt_workflow.png" else 10.5 * cm
        st += [KeepTogether([img(DOCS / "diagrams" / fname, max_h=h), P(cap, "cap")])]
    st.append(PageBreak())
    st.append(P("(c) Prompt sheets (one per final prompt)", "h2"))
    t01 = load_out(FINAL_V, "T01")
    inp = TESTS["T01"]["input"]
    st += prompt_sheet("P1", "Skill Normaliser", "Step 1 of 4 (first LLM call)",
                       "Turn free-text skills into canonical skill names with levels; reject junk or injection text.",
                       {"skill_vocabulary": "the 53 canonical skills with aliases (from code/kb/skills.json)",
                        "student_skills": "the student's free-text skills exactly as typed"},
                       1, "JSON: status, skills[name, level, evidence], unrecognised[], message",
                       f"student_skills = \"{inp['student_skills']}\"", step_out(t01, "P1"))
    st.append(PageBreak())
    st += prompt_sheet("P2", "Role Requirements (grounded)", "Step 2 of 4 (after role retrieval)",
                       "Match the typed role to a known role profile and return its must-have / good-to-have skills; flag vague roles.",
                       {"target_role": "the role exactly as typed by the student",
                        "candidate_roles": "top-3 role profiles retrieved from code/kb/roles.json with match scores (JSON)",
                        "all_role_names": "names of all 13 roles, used for suggestions"},
                       1, "JSON: status, matched_role, confidence, must_have[], good_to_have[], suggested_roles[], message",
                       f"target_role = \"{inp['target_role']}\"; retrieved = "
                       + ", ".join(f"{r['name']} ({r['match_score']})" for r in (t01 or {}).get("retrieval", {}).get("roles", [])),
                       step_out(t01, "P2"))
    st.append(PageBreak())
    st += prompt_sheet("P3", "Gap Analyser", "Step 3 of 4",
                       "Compare the student profile with the role requirements; rank gaps, estimate hours, compute readiness.",
                       {"student_profile": "P1 output (skills with levels), JSON",
                        "role_requirements": "P2 output (matched role, must-have, good-to-have), JSON",
                        "effort_table": "hours per level for the required skills (from skills.json)"},
                       1, "JSON: gaps[rank, skill, type, current_level, required_level, priority, est_hours, reason], strengths[], readiness_score, summary",
                       "student_profile = P1 output above; role_requirements = P2 output above", step_out(t01, "P3"))
    st.append(PageBreak())
    st += prompt_sheet("P4", "Plan Builder (grounded)", "Step 4 of 4 (after resource retrieval)",
                       "Build a week-wise plan within the hour limit using only retrieved resource IDs, with practice tasks; defer what does not fit.",
                       {"gaps": "P3 ranked gaps (JSON)", "weekly_hours": "study hours per week (number)",
                        "num_weeks": "number of weeks (number)",
                        "resources": "free resources retrieved for the gap skills: id, title, type, skills, level, hours (no URLs)"},
                       1, "JSON: status, weeks[week, focus_skills, items[resource_id, activity, hours], practice_tasks[task, hours], total_hours], deferred_gaps[], notes",
                       f"weekly_hours = {inp['weekly_hours']}, num_weeks = {inp['num_weeks']}, gaps = P3 output, resources = "
                       + ", ".join((t01 or {}).get("retrieval", {}).get("resource_ids", [])), step_out(t01, "P4"))
    st.append(PageBreak())

    # 3. Implementation
    st += [P("Section 3: Implementation", "h1"), P("What is built", "h2"),
           P("A working Streamlit web app runs the full prompt chain on Gemini. The user types skills, a role, hours per week and weeks, or clicks "
             "one of five example inputs. The app shows each step's progress, the matched role, the readiness score, the ranked gap table, "
             "week cards with resource links and practice tasks, deferred gaps, and the automatic checks. An expandable trace shows every "
             "rendered prompt and raw model output. A sidebar switch runs v1, v2, v3 or v4, so the improvement can be shown live. "
             "A separate experiment runner scores every version on the test set and saves all outputs in the repository.", "body"),
           P("Module status", "h2"),
           table([["Module", "What it does", "Status", "Notes"]] + [[E(a), E(b), f"<b>{E(c)}</b>", E(d)] for a, b, c, d in MODULES],
                 [3.6 * cm, 6.4 * cm, 2.2 * cm, 4.8 * cm]),
           P("Prompt iteration log", "h2"),
           table([["Version", "What changed", "Why it was changed", "Result after the change (measured on the 14-input test set)"]]
                 + [[f"<b>{v}</b>", E(what), E(why), E(version_result_text(v))] for v, what, why in ITERATIONS],
                 [1.3 * cm, 5.0 * cm, 4.2 * cm, 6.5 * cm]),
           Spacer(1, 6),
           P("Full text of each version", "h3"),
           P("All four versions were run on the same 14 inputs with the same model; numbers come from test-data/results.json.", "small"),
           P("<b>v1 (baseline, single prompt, default settings, plain text):</b>", "small")]
    import sys
    sys.path.insert(0, str(ROOT / "code"))
    from skillit.prompts import load_prompt
    st.append(mono(load_prompt("v1", "P0")["user"]))
    st.append(P("<b>v2 (4-step chain, JSON asked in text, default temperature, no grounding, no examples):</b>", "small"))
    for pid in ("P1", "P2", "P3", "P4"):
        p = load_prompt("v2", pid)
        st.append(mono(f"[{pid}] SYSTEM: {p['system']}\nUSER:\n{p['user']}"))
    st.append(P("<b>v3 (4-step chain with rules, examples, JSON mode, grounding):</b> P1, P2 and P4 are identical to the final "
                "prompt sheets in Section 2(c). Only P3 was different; its full v3 text:", "small"))
    p = load_prompt("v3", "P3")
    st.append(mono(f"[P3 v3] SYSTEM:\n{p['system']}\nUSER:\n{p['user']}", max_lines=60))
    st.append(P("<b>v4 (final):</b> the four prompt sheets in Section 2(c) (prompts/final/).", "small"))
    st.append(PageBreak())

    # 4. Demonstration and testing
    v3rows = [r for r in ROWS if r["version"] == FINAL_V]
    st += [P("Section 4: Demonstration and testing", "h1"),
           P(f"Test table: final version (v4) on {len(v3rows)} made-up inputs "
             f"({sum(r['type']=='Normal' for r in v3rows)} normal, {sum(r['type']=='Edge' for r in v3rows)} edge, "
             f"{sum(r['type']=='Invalid' for r in v3rows)} invalid). Pass/Fail is decided by the rule-based checks in "
             "code/skillit/validate.py: status, JSON, week count, hour limit, curated resources, no false gaps, plus the expectations of each test.", "body"),
           table([["Test no.", "Input (short)", "Type", "Expected output", "Actual output (short)", "Pass / Fail"]]
                 + [[r["test"], E(r["input_short"]), r["type"], E(r["expected"]),
                     E(r["actual"]) + (f"<br/><font color='#B91C1C'>{E(r['reasons'])}</font>" if r["reasons"] else ""),
                     f"<b><font color='{'#15803D' if r['pass'] else '#B91C1C'}'>{'Pass' if r['pass'] else 'Fail'}</font></b>"]
                    for r in v3rows],
                 [1.2 * cm, 3.6 * cm, 1.3 * cm, 4.2 * cm, 5.3 * cm, 1.4 * cm]),
           Spacer(1, 8), P("Same test set on all four versions", "h3"),
           table([["Metric"] + VERS] + [[E(lbl)] + [E(str(fn(SUMMARY[v]))) for v in VERS] for lbl, fn in COMPARE],
                 [6.2 * cm, 2.7 * cm, 2.7 * cm, 2.7 * cm, 2.7 * cm]),
           P(f"All versions ran on the same model ({E(MODEL)}). Measured by the same automatic checks.", "small"),
           PageBreak(), P("Screenshots of real runs", "h2")]
    for fname, cap in SCREENSHOTS:
        st += [KeepTogether([img(DOCS / "screenshots" / fname, max_h=10.5 * cm), P(cap, "cap")])]
    st += [P("Known limitations and what we will try next", "h2")] + bullets([E(x) for x in LIMITATIONS])
    st.append(PageBreak())

    # 5. Repository
    st += [P("Section 5: Repository", "h1"), P(f"Repository: {link(L['repository'])}", "body"),
           img(DOCS / "screenshots" / "repo.png", max_h=11 * cm), P("Screenshot: repository home page", "cap"),
           P("What changed since Milestone 1", "h3")]
    st += bullets(["Added prompts/v1 (baseline), prompts/v2 (first chain), prompts/v3 (rules, examples, grounding) and prompts/final (v4, the four final prompts). The app reads these files directly.",
                   "Added code/: the Streamlit app, the prompt chain, Gemini client, retrieval, validators, experiment runner and link checker.",
                   "Added code/kb/: 53 skills with aliases, 13 role profiles and 64 free resources for grounding.",
                   "Added test-data/: 14 test inputs, the saved outputs of every run (v1, v2, v3) and results.csv / summary.md.",
                   "Added docs/ (diagrams, this PDF, build script) and CHANGELOG.md with dated entries. No API key is in the repository."])
    st.append(PageBreak())

    # 6. Supporting document
    st += [P("Section 6: Supporting document (Technical Report)", "h1"),
           P(f"Same document as uploaded at Q16: {E(team['team_name'].title().replace(' ', ''))}_TechnicalReport.pdf", "small")]
    st += technical_report_flow(in_m2=True)
    st.append(PageBreak())

    # 7. Team contribution
    st += [P("Section 7: Team contribution", "h1"),
           table([["Member name", "Enrollment no.", "Role", "Tasks done in Milestone 2", "Evidence", "Contribution (%)"]]
                 + [[E(m["name"]), E(m["enrollment"]), E(m["role"]), E(m["tasks"]), E(m["evidence"]), str(m["percent"])] for m in team["members"]]
                 + [["<b>Total</b>", "", "", "", "", f"<b>{sum(m['percent'] for m in team['members'])}</b>"]],
                 [2.6 * cm, 2.4 * cm, 2.6 * cm, 4.2 * cm, 3.8 * cm, 1.4 * cm]),
           Spacer(1, 10), P("All members have read and agreed to this contribution table.", "body")]
    doc.build(st, onFirstPage=footer, onLaterPages=footer)


MODULES = json.loads((DOCS / "modules.json").read_text(encoding="utf-8")) if (DOCS / "modules.json").exists() else []
SCREENSHOTS = [("T01.png", "Screenshot 1: Test T01 (Data Analyst, 6 h/week, 4 weeks), readiness score, gap table and week plan"),
               ("T07.png", "Screenshot 2: Test T07 (messy text 'py, ML, js, reactjs, gud at excell...' matched to Full Stack Developer)"),
               ("T10.png", "Screenshot 3: Test T10 (vague role 'any IT job with good salary'): chain stops and suggests roles")]
COMPARE = [
    ("Tests passed (of 14)", lambda s: s["passed"]),
    ("Valid JSON runs", lambda s: s["json_valid_runs"] if s is not SUMMARY["v1"] else "0 (plain text)"),
    ("Plans made", lambda s: s["plans_made"]),
    ("Plans within the hour limit", lambda s: s["plans_within_hours"]),
    ("Resources from curated list / total", lambda s: f"{s['resources_from_curated_list']}/{s['resources_total']}"),
    ("Runs with false gaps", lambda s: s["runs_with_false_gaps"]),
    ("Edge + invalid tests passed (of 8)", lambda s: s["edge_invalid_passed"]),
    ("T01 x3 gap-list consistency (Jaccard)", lambda s: (s.get("consistency_T01") or {}).get("mean_jaccard", "n/a")),
]


def build_report(path):
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title="Skill-it Technical Report", author=team["team_name"])
    doc.build(technical_report_flow())


if __name__ == "__main__":
    tid = team["team_id"] if team["team_id"] and " " not in team["team_id"] else team["team_name"].title().replace(" ", "")
    out1 = DOCS / f"M2_{tid}_{team['project_short']}.pdf"
    out2 = DOCS / f"{team['team_name'].title().replace(' ', '')}_TechnicalReport.pdf"
    build_m2(out1)
    build_report(out2)
    print("Wrote", out1, "and", out2)
