# Review harness: rules for agents

You are usually running inside one pipeline step (READ or WRITE) started by `harness/pipeline/stages.py`.
The prompt names the one file you must write. Rules that apply to every step:

- Follow the prompt's steps in order and nothing else. Open only the files the prompt lists; do not
  read harness code, tests, config or other jobs (the prompt already carries every rule you need).
- Write only the file the prompt names, inside `jobs/<job>/`. Do not edit code, config, other jobs,
  prompts or docs. Do not delete or move any file.
- agy: use file tools only (read_file, list_dir, write_to_file). Shell commands are refused in headless
  mode and end the session without a result.
- Never invent plot, dialogue, names or timestamps. Everything comes from the film itself (proxy video,
  frame sheets, subtitle sheets, transcript) or from the approved `timeline.md`. If something is not
  visible or audible, say so in the file.
- Timestamps are seconds from the start of the source video. In proxy chunks, use the timecode burned
  into the top-left corner, never the chunk's own clock.
- Editorial rules (Vietnamese): `docs/editorial-guidelines.md`. Review length 40-50 % of the source,
  including exactly one final `assessment` segment of 10-20 s spoken. Durations are decided later by real
  TTS; never pad with silence or slow speech.
- Allowed helper commands (claude only): `./run.sh frame <job> <seconds>...` saves full-size frames and
  prints their paths; `./run.sh check <job>` validates `review.json` and estimates its spoken length.
- No network calls, no package installs, no API keys.

## For people changing the harness

- Python package `harness/`; run tests with `.venv/bin/python -m unittest discover -s tests`.
- Dashboard page: edit `harness/monitor/static/index.src.html`, then rebuild the served ASCII-only page
  with `.venv/bin/python -m harness.monitor.asciify` (a test fails when `index.html` is stale).
- Change timing/schema logic only with tests; real measured TTS and the rendered file stay authoritative.
