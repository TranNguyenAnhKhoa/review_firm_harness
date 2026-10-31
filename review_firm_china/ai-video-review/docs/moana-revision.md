# Moana — revision and measured narration

## Files

- Original, preserved: `input/scripts/review.moana.json`.
- First expanded draft, preserved: `input/scripts/review.moana.v2.json`.
- Current picture-sampled revision: `input/scripts/review.moana.v3.json`.
- Curated additional commentary: `input/scripts/moana.editorial-additions.md`.
- Provenance/uncertainty: `data/timeline/moana/review_v3_editorial.json`.
- TTS artifacts remain in `output/moana_v2/` (the work directory was started with v2;
  consult `measurement_progress.json` and the final review SHA-256, not the directory name).

No original video, timeline, script, or prior final render was overwritten.

## Editorial changes

The 28-paragraph original became 99 ordered visual/narration segments with explicit
speech-unit emotions. Added commentary concerns already-described character choices,
relationships and situational humor, not fabricated plot events. Several unsupported
precise claims and literal exaggerated details were removed. The assessment was rewritten
as a personal observation, without asserting release year, remake fidelity or cast facts.

The source timeline declares `partial`. This revision does **not** upgrade that status.
We inspected 99 midpoint frames and 121 more densely sampled frames around suspected errors.
Pictures showed credit/title graphics already at 6330 seconds; the former 6330–6375
story/assessment range was unsuitable. The revised story ends by 6325 seconds, and the
assessment uses an earlier story image range. Cave/departure, Tamatoa escape, first battle,
Tala apparition, final confrontation and homecoming windows were also corrected from samples.
Practice was moved before the intimate backstory conversation, as indicated by the samples.

Pictures did not substantiate the original specific shell-placement account; the homecoming
description was made more conservative. Sampled subtitles are evidence only for the sampled
moments, not a full transcript or verification of every quoted line in the inherited narration.

Subranges within those chapters remain **editorial estimates**, not frame-accurate scene cuts.
Continuous picture/voice review is still required before signing off a final video. The sidecar
keeps `render_ready: false`; this is deliberate. Do not claim all dialogue, sounds, or actions
have been verified simply because the metadata/schema pass.

## TTS measurement

Use the existing presets and bounded speech-rate adaptation. No rate reduction, added silence,
video loops or held frames are used to manufacture the required overall ratio.

```powershell
.\.venv\Scripts\python.exe scripts/measure_review.py `
  --video "input/videos/Hành Trình Của Moana - Moana (2026) - Phimmoichill.mp4" `
  --review input/scripts/review.moana.v3.json `
  --reuse-review input/scripts/review.moana.v2.json `
  --config config/moana.v3.yaml `
  --output-dir output/moana_v2 --workers 3
```

The script only synthesizes audio and writes measurement/debug files. It never renders.
Rerunning reuses a segment only after checking its input/config/code fingerprint, audio and
debug SHA-256 and measured WAV duration. Visual-only changes do not invalidate speech.
Text/emotion/section/ID/voice/settings changes do invalidate it. Separate silence caches prevent
parallel workers from racing to write the same WAV. Network errors are not replaced by silence.

`--ids` selects a calibration subset and never certifies whole-review duration.
An interrupted run has no valid whole-review conclusion. The final `review_timing.json`
must have `passed: true` and its review hash must match the current JSON.

Required total: 2775.7691064–3469.711383 seconds, including the final 10–20-second assessment.
Aim: 3122.7402447 seconds. Assessment speech and assessment timeline are checked separately.
Text counts and extrapolation from incomplete audio are estimates only.

`config/moana.v3.yaml` changes duration-matching fallback to `error`, so insufficient footage
cannot be silently filled with held frames. The file inherits all voice/pause settings unchanged.

## Verification

37 unit/integration tests passed after adding measurement-cache regression tests.
Speaker performance still needs listening review; emotion labels are not proof of natural acting.
Source subtitles are burned in; choose final subtitle placement after picture review to avoid overlap.
Do not crop/cover source graphics automatically as part of this narration-only task.

## Measured result (2026-10-04)

- All 99 segments / 649 speech units synthesized; no skipped units or silent fallback.
- PCM narration including preset pauses: **3193.775 seconds (53:13.775)**.
- Edit timeline, rounded up per segment to 25 fps: **3195.560 seconds (53:15.560)**.
- Ratio to 6939.422766-second source: **46.0494% — PASS**.
- Final assessment speech: **14.400 seconds**; frame-rounded timeline: **15.560 seconds — PASS**.
- Speech-only total: 3002.976 seconds; configured inserted pauses: 190.799 seconds.
- All 99 source windows pass duration matching with `fallback: error`; zero held-frame padding,
  no source boundary overruns. Computed video speed factors: 1.0–1.0988577 (no slowdown needed).
- Emotions: normal 395, suspense 35, excited 23, serious 42, punchline 44, calm 110.
- 77 units remain outside their approximate token-rate band after bounded adaptation;
  they were retained and logged, not regenerated indefinitely or falsely marked within range.
- Original review SHA-256 still matches the saved pre-edit fingerprint.
- Timing report hash matches `review.moana.v3.json`; `rendered: false`.
- Full MP3 decode: PASS; WAV/MP3 duration: 3193.775 seconds.
- All 1078 ASS events lie inside actual speech-unit intervals (centisecond rounding tolerance);
  intentional inserted pauses are excluded. Audio index duration matches the PCM file.

Artifacts:

- `output/moana_v2/review_timing.json`: measured editorial checks.
- `output/moana_v2/audio/preview_90s.mp3`: first 90 seconds for quick listening.
- `output/moana_v2/listening/moana_narration.wav` and `.mp3`: full audio-only listening package.
- `output/moana_v2/listening/moana_narration.ass`: speech-unit subtitles for that audio-only package.
- `output/moana_v2/listening/audio_index.json`: audio-only segment offsets.

Listening-package offsets use exact PCM durations; final video offsets add tiny per-clip
frame-rounding gaps. Do not substitute those two subtitle timelines without recalculating offsets.
The measurement/listening stage above did not render video. A separate check-render stage
is described below; it does not certify the provisional source subranges editorially.

## Check render from verified speech

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/render_measured_review.py `
  --video "input/videos/Hành Trình Của Moana - Moana (2026) - Phimmoichill.mp4" `
  --review input/scripts/review.moana.v3.json `
  --tts-dir output/moana_v2 `
  --config config/moana.render.yaml `
  --output-dir output/moana_render_v3 --workers 2 --threads 3
```

This path performs **no TTS requests**. It validates the review hash, all 99 speech cache
fingerprints/audio/debug hashes and decoded audio durations before rendering. Source and
review are hashed again before certification. It preserves the JSON list order (IDs are not
chronologically sorted), and measures video offsets with per-segment frame rounding.

Each source range is trimmed, safely retimed, mixed with its own narration and subtitled in
one pass. Intermediate MKVs contain H.264 + 48 kHz stereo PCM. Sequential concat copies the
video stream and encodes AAC once, avoiding a 99-input filter graph and per-cut AAC priming.
The final file is published only after timing/codec/dimensions checks and a complete FFmpeg
video/audio decode with errors treated as failures.

Configuration: original 1920x800 aspect/resolution, 25 fps, libx264 veryfast, CRF 20,
yuv420p, AAC 192 kb/s. Lowered original background uses volume 0.18; Demucs is off.
Mix peak limiting is delay-compensated. Speech was already normalized at the narration stage.
Review subtitles use top alignment, 40-pixel font and a 60-pixel vertical margin to avoid
the burned-in bottom source subtitles. No source graphics are removed or covered by a mask.

If interrupted, rerun the same command. Completed segments are reused only when the render
manifest fingerprint and intermediate hash match. Changing inputs/settings/render code
requires a **new output directory**; older final videos are never silently overwritten.
Use the original pipeline for Demucs-enabled or resolution-changing workflows; the cached
renderer explicitly rejects these currently unsupported options rather than ignoring them.

Artifacts under `output/moana_render_v3/`:

- `render_progress.json`: completed segment indexes and status.
- `render_manifest.json`: inputs/config/code fingerprint and provenance.
- `edl/review.json`: actual voice durations, source selections and video timeline offsets.
- `subtitles/review.ass`: subtitles on the video timeline, not the audio-only timeline.
- `final/final_review.mp4`: published only after successful render and full decode validation.
- `review_timing.json`: final encoded duration and validation result.

39 local regression tests passed, including exact-frame PCM concat, vertical Unicode ASS,
bounded footage selection, narration truncation rejection and the existing voice pipeline.
Technical PASS does not mean every picture/line match or voice performance has been approved.

## Completed check render (2026-10-04)

- Final: `output/moana_render_v3/final/final_review.mp4`.
- 99/99 segments completed, no TTS regenerated and no original source/script overwritten.
- Actual encoded duration: **3195.560 seconds / 53:15.56**, **46.0494%** of source — PASS.
- Assessment starts at **53:00.00**, lasts **15.56 seconds** on screen, with **14.40 seconds**
  of real speech — PASS.
- Video: H.264, yuv420p, 1920x800, 25 fps, **79,889 frames**.
- Audio: AAC, 48 kHz stereo; video and audio both start at 0 and last 3195.560 seconds.
- Full video/audio decode with FFmpeg `-xerror`: **PASS**.
- Size: **1,478,183,511 bytes** (about 1.48 GB decimal).
- Seven six-second waveform samples at segment indexes 1, 17, 33, 49, 65, 81, 99:
  measured lag **0 ms** against original narration WAVs; correlations 0.9832–0.9998 — PASS.
- All **1078 subtitle events** stay within their speech-unit intervals (centisecond rounding
  tolerance), excluding intentional pauses — PASS.
- Source-range audit: no overruns or duration-matching freeze padding.
- Spot-checked rendered frames at indexes 1, 8, 17, 25, 32, 49, 54, 80, 98, 99:
  Vietnamese glyphs and top placement render correctly; source graphics/aspect remain intact.
  The last story/assessment samples are film scenes, not credits.
- Render, concat and full decode validation took about **31 minutes** on this CPU.

Recheck audio/subtitle alignment without rebuilding:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/check_render_alignment.py --output-dir output/moana_render_v3
```

Results: `output/moana_render_v3/review_timing.json` and
`output/moana_render_v3/qc/final_alignment.json`.
Final SHA-256: `14ccecf2d258bcfb4aac199c4c7506c958a585773ccf6cfeb7e3901a56b3e470`.

This remains a **check render**, not an editorially approved master: source windows within
chapters are provisional, not sentence-level best-shot selections. The inherited READ status
stays `partial`. Waveform alignment does not judge naturalness, pronunciation, humor or whether
every described action is visible at that exact moment. Original dialogue is still present at
reduced volume (Demucs was not run). Watch/listen to this version to select further refinements.
