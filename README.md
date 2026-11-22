# Skill-it: Skill Gap Analyser and Learning Plan Builder

**SCSE4041 Prompt Engineering, Mini Project (Milestone 2)**
Team **SPARTANS DO CODE**, Bennett University

🔗 **Prototype:** https://skillit-spartans.streamlit.app
🎬 **Reel:** REEL_LINK

## What it does
B.Tech students often know their dream job but not which skills they are missing or how to fit learning into their week.
Skill-it takes three things:

* the skills the student already has (free text, any format)
* the target job role
* the hours per week and number of weeks the student can study

It returns a **ranked list of skill gaps**, a **readiness score** and a **week-by-week plan**. Every week stays within the hour limit and uses free resources from a curated list, with a practice task each week.

The prompt workflow is the core of the project. **Four prompts run in a chain:**

| Step | Prompt | Input → Output |
|---|---|---|
| P1 | Skill Normaliser | free-text skills → standard skill names + levels (JSON) |
| P2 | Role Requirements (grounded) | typed role + 3 retrieved role profiles → must-have / good-to-have skills (JSON) |
| P3 | Gap Analyser | P1 + P2 → ranked gaps, estimated hours, readiness score (JSON) |
| P4 | Plan Builder (grounded) | gaps + hours + retrieved free resources → week-wise plan (JSON) |

Rule-based checks in code (`code/skillit/validate.py`) then verify:

* the JSON is valid
* the plan has the right number of weeks
* every week is within the hour limit
* every resource ID comes from the curated list
* no skill the student already has is listed as a gap
* the readiness score follows the formula

Model: **Google Gemini** (`gemini-3.5-flash-lite`, free tier) through the REST API, with automatic fallback to another Gemini model if the free quota runs out.

## Repository structure
```
README.md
prompts/
  v1/      baseline single prompt (Milestone 1)
  v2/      first 4-step chain (JSON in text, no grounding)
  v3/      chain with rules, examples, JSON mode and grounding
  final/   final prompts (v4) P1-P4: v3 + readiness working in P3 (the app reads these files)
code/
  app.py               Streamlit prototype
  run_experiments.py   runs v1/v2/v3/v4 on all test inputs and scores them
  check_links.py       checks every resource URL opens
  skillit/             chain, retrieval, Gemini client, validators
  kb/                  skills.json, roles.json, resources.json (knowledge base)
test-data/
  test_inputs.json     14 test inputs (6 normal, 5 edge, 3 invalid)
  outputs/             full saved runs per version (prompts sent + raw outputs)
  results.csv/json     pass/fail and metrics
  summary.md           version comparison
docs/                  diagrams, screenshots, Milestone 2 PDF
CHANGELOG.md
```

## How to run
```bash
pip install -r requirements.txt
# get a free key at https://aistudio.google.com -> Get API key
export GEMINI_API_KEY="your-key"          # Windows PowerShell:  $env:GEMINI_API_KEY="your-key"
streamlit run code/app.py                 # the prototype
python code/run_experiments.py --model gemini-3.5-flash-lite   # re-run all experiments (~20 min on the free tier)
```
The key is read from an environment variable or Streamlit secrets. **It is never stored in this repository** (`.streamlit/secrets.toml` is git-ignored).

## Responsible use
* All test profiles are made up. The app asks users not to enter names, IDs or contact details.
* The model never writes links: it can only pick resource IDs from the curated list, and the app adds the real URLs.
* Student text is treated as data (prompt-injection test T13).
* Plans are suggestions. The app tells students to check them with a mentor.

## Team
| Member | Enrollment no. | Role |
|---|---|---|
| Vansh Chaudhary (leader) | S24CSEU1734 | Prompt chain, retrieval, Streamlit app, P3 + P4 prompts, experiment runner |
| Vanshika | S24CSEU1688 | Knowledge base, test set, diagrams, report, reel |
| Smarth Bhardwaj | S24CSEU1784 | P1 + P2 prompts, rule-based checks, link checker |
