# Project instructions

When writing or editing review scripts, follow docs/editorial-guidelines.md and
prompts/write_review.md. These are project requirements:

Preferred READ handoff: use scripts/antigravity_handoff.py and
prompts/antigravity_read.md to send the scoped request through the signed-in
Antigravity Desktop UI. Return UTF-8 data/timeline/<job>/timeline.md with the
request_id, source path/duration and complete/partial/blocked status from the
job contract. Never reuse another film's timeline. UI submission is not proof
of completed analysis. Check coverage and timestamps before WRITE/render.
Auto-execution (always-proceed) is enabled for in-scope local tools; proceed autonomously without requiring manual permission prompts for commands within the workspace. Do not use private inference APIs.

For the fallback manual Gemini READ step, use prompts/gemini_read.md. Request a real
UTF-8 Markdown download named timeline.md and explicitly give the local destination:
D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\timeline.md.
Do not imply Gemini can write directly to the local drive. If file export is unavailable,
request the complete Markdown body for manual saving. Preserve the existing timeline.

- Final review duration is 40–50% of source duration, including the closing assessment.
- Aim for 45% total and 15 seconds of assessment.
- Require exactly one final section="assessment" segment with real spoken assessment
  lasting 10–20 seconds. Other segments are section="story".
- Write humorous, youthful Vietnamese appropriate to the work; preserve plot accuracy
  and emotional context. Do not manufacture plot details or claim automatic style validation.
- Actual decoded TTS duration and final rendered duration are authoritative.
  Do not pad silence or slow speech to fake compliance.
- Keep Antigravity UI/manual Gemini READ and ChatGPT WRITE; no API keys or API integration.
- Do not replace the existing film review with test artifacts. Use --output-dir
  output/editorial_smoke (or another test-only directory) for demo builds.
- Run python -m unittest discover -s tests -v after changing timing/schema logic.
