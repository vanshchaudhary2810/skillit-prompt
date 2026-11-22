# Milestone 2 form: answers (copy-paste)

Items in CAPITALS (like TEAM_ID) are filled in once we have the real results and links.

| Q | Answer |
|---|---|
| 1 Team ID | TEAM_ID |
| 2 Team name | SPARTANS DO CODE |
| 3 Project title | Skill-it: Skill Gap Analyser and Learning Plan Builder |
| 4 Team leader name | VANSH CHAUDHARY |
| 5 Leader enrollment no. | S24CSEU1734 |
| 6 Group (batch) | B49-64 (Vansh and Smarth: batch 59, Vanshika: batch 57) |
| 7 Enrollment numbers (one per line) | S24CSEU1734<br>S24CSEU1688<br>S24CSEU1784 |
| 8 Project type (max 2) | Custom web app (Streamlit) · Prompt chain / workflow with RAG grounding *(pick the 2 closest options shown in the form)* |
| 9 Main AI tool and model | Google Gemini API, gemini-3.5-flash-lite (free tier), called from a Streamlit web app |
| 10 Number of prompts | 4 |
| 11 Prototype link | https://skillit-spartans.streamlit.app |
| 12 Repository link | https://github.com/vanshchaudhary2810/skillit-prompt |
| 13 Reel link | https://drive.google.com/drive/folders/1SGWkSHRiEF57uFlfx6jch0U3YTDm5Yem?usp=drive_link |
| 14 Reel length (s) | 96 |
| 15 Supporting document type | Technical report |
| 16 Upload | SpartansDoCode_TechnicalReport.pdf |
| 17 Number of test inputs | 14 |
| 18 Number of prompt versions | 4 |
| 19 Prototype status | Some modules working |
| 20 Working modules (one per line) | see list below |
| 21 Upload M2 PDF | M2_TEAM_ID_SkillIt.pdf |
| 22 Main task of each member | see lines below |
| 23 Anything the evaluator should know | see text below |
| 24 Confirmation | Tick only after all 3 members agree to Section 7 |

**Q20 (exactly as in the module status table):**
```
P1 Skill Normaliser
P2 Role Requirements + role retrieval
P3 Gap Analyser
P4 Plan Builder + resource retrieval
Validator (automatic checks)
Streamlit web app
Experiment runner
```

**Q22:**
```
S24CSEU1734 – Vansh Chaudhary – Built the prompt chain, retrieval and Streamlit app; deployed it; wrote P3 (v2–v4, incl. the v4 readiness fix) and P4, and the experiment runner
S24CSEU1688 – Vanshika – Curated the knowledge base (roles, skills, resources); wrote the 14 test inputs; diagrams, M2 PDF, technical report and reel
S24CSEU1784 – Smarth Bhardwaj – Wrote P1 and P2 (v2–v3) with the invalid-input/vague-role/injection rules; rule-based checks; link checker
```

**Q23:**
```
Open the prototype link and click any "Try an example" button in the sidebar, then "Build my plan". No login needed.
Use the sidebar "Prompt version" switch to compare the baseline (v1) with the final chain (v4).
"See every prompt and raw model output" shows the full prompt trace.
If the free API quota is busy, wait 1 minute and retry, or paste your own free Gemini key in the sidebar (it is not stored).
All test results: test-data/results.csv in the repository.
```
