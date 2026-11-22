# Skill-it reel: script (target 120-135 seconds, must stay between 90 and 150)

Record the screen (Mac: Cmd+Shift+5 → "Record Entire Screen", or QuickTime → New Screen Recording).
A teammate reads the voice-over. Use the **deployed app** in Chrome at 110-125% zoom so the text is readable.
Upload to Google Drive → Share → "Anyone with the link: Viewer". Note the exact length in seconds for Q14.

| # | Time | Show on screen | Voice-over (read at a calm pace) |
|---|---|---|---|
| 1 Problem | 0:00-0:12 | App home page with the title "Skill-it" | "Most of us know the job we want, but not which skills we are missing or how to fit learning into a busy week. Skill-it builds a personalised plan for B.Tech students in seconds." |
| 2a Old prompt | 0:12-0:32 | Sidebar → **Baseline single prompt (v1)** → example "Data analyst (6 h/wk)" → Build. Scroll the plain-text answer and the check line under it. | "This was our Milestone 1 prompt: one mentor prompt. The answer looks fine, but it is plain text, so code cannot check it. Hours per week are not always clear, and the links are not from any list we trust." |
| 2b Improved prompt | 0:32-0:52 | Switch to **Final chain (v4)** → same example → Build. Show the 4 green step ticks, then the green "Automatic checks". Open the "See every prompt" expander for 2 seconds. | "Our final version splits the job into four prompts: normalise skills, role requirements, gap analysis and the plan. Each has rules, a JSON schema, one example and temperature 0.2, plus grounding from our role and free-resource lists. On our 14 test inputs this took us from 0 out of 14 passing tests to 13 out of 14, and from 3 trusted links out of 26 to 56 out of 56." |
| 3 Demo | 0:52-1:50 | (a) Type a new profile, e.g. skills `C++, solved 150 leetcode, OOP, git`, role `Software Development Engineer`, 8 hours, 6 weeks → Build. Show the readiness score, gap table and 2 week cards; click one resource link. (b) Click the example "Messy input → MERN": show "reactjs → React" in the trace. (c) Click "Vague role": the app stops and suggests roles. | "Here is a live run. It matched the role, gave a readiness score, ranked the gaps and built a six-week plan. Every week stays under eight hours, and every resource is a real free link from our curated list. It also understands messy text like 'reactjs' or 'gud at excell'. For a vague role like 'any IT job', it stops and suggests real roles instead of guessing. Prompt-injection text is treated as data, not instructions." |
| 4 Progress | 1:50-2:10 | GitHub repo page (prompts/v1, v2, final, test-data) | "Done so far: four working prompts, three prompt versions, a 14-input test set with automatic scoring and a public app. For Milestone 3 we will compare ChatGPT and Claude, compute readiness in code, and refresh roles from live job postings. Thank you!" |

Tips
- Do one full rehearsal first. If the free quota hits its limit during recording, wait a minute and retry. Never fake a screen.
- Keep the final video under 150 s. Trim the start and end in QuickTime (Cmd+T).
- Captions are optional. If you add them, CapCut's auto-captions work fine.
