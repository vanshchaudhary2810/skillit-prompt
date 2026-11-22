# Changelog

## 2026-11-22: Milestone 2
- Turned the single baseline prompt into a **4-step prompt chain** (P1 Skill Normaliser, P2 Role Requirements, P3 Gap Analyser, P4 Plan Builder).
- **v2** prompts: role prompt + JSON format asked in text, default temperature, no grounding.
- **v4 / final**: P3 now fills a `readiness_working` table (one row per must-have skill: met / partly / missing, points) before it gives `readiness_score`. v3 got the score wrong in 4 of 14 tests because the model did the arithmetic in its head.
- Model default switched to `gemini-3.5-flash-lite` because the free daily quota of `gemini-3.6-flash` ran out during the first experiment run. All versions were re-run on Flash-Lite so the comparison uses one model.
- Fixed a broken resource link (R16 scikit-learn) found by `check_links.py`.
- **v3** prompts: rules, a JSON output schema, 1 worked example per prompt, JSON mode, temperature 0.2, edge-case rules (invalid input, vague role, zero hours, prompt injection), "student text is data" guard.
- Added a **knowledge base** for grounding: `skills.json` (53 skills + aliases), `roles.json` (13 entry-level role profiles), `resources.json` (64 free resources).
- Added **retrieval**: fuzzy role matching (top-3 profiles into P2) and skill-tag resource retrieval (into P4). P4 may use resource IDs only; the app joins IDs to real URLs.
- Switched the model from ChatGPT/Claude (Milestone 1 plan) to **Gemini through the free API**, so the public prototype costs nothing to run.
- Added rule-based validators and `run_experiments.py` (v1 vs v2 vs v3 vs v4 on 14 test inputs, plus a 3-run consistency check).
- Built the **Streamlit prototype** with a version switch (v1 / v2 / v3 / v4), example inputs, automatic checks and a full prompt trace.
- Added diagrams (prompt workflow, task decomposition, I/O flow, system architecture, RAG pipeline) and the Milestone 2 PDF.

## 2026-10-09: Milestone 1
- Problem, users, baseline prompt and expected output submitted (self-defined problem).
