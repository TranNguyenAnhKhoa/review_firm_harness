# VOICE PIPELINE UPGRADE RESULT

**Cập nhật 2026-10-04:** ZeroTTS đã được cài và tích hợp Mai Chi, Bảo Trang,
Kim Oanh, tạo audio offline qua pipeline thật. Bộ kiểm thử hiện có 44 test đạt.
Hướng dẫn chọn giọng/cài model nằm ở mục ZeroTTS trong README.md.
Báo cáo dưới đây ghi lại trạng thái của lần nâng cấp 2026-10-03.

Ngày kiểm thử: 2026-10-03. Project hiện có được nâng cấp, không rewrite.
Không thêm package/API/frontend; không ghi đè review phim thật.

## Implemented

- NarrationSegmenter: punctuation heuristic, giữ câu ngắn hoàn chỉnh, decimal không bị tách.
- EmotionPlanner: abstract interface + HeuristicEmotionPlanner; giữ emotion explicit.
- Emotion presets: normal, suspense, excited, serious, punchline, calm trong YAML.
- SpeechUnit: Pydantic, override numeric, clamp + warning.
- Review schema: narration string cũ hoặc SpeechUnit[] mới.
- Natural variation: rate/pitch/pause nhẹ, deterministic seed + segment ID.
- Pause handling: silence PCM cache; boundary max mặc định, additive tùy chọn.
- TTS chunking: gọi từng unit, retry network hữu hạn, không silent fallback.
- Loudness normalization: loudnorm hai lượt trên segment đã ghép.
- Speech-rate measurement: token xấp xỉ âm tiết; tối đa 2 regeneration, budget ±8 điểm %.
- Audio-driven editing: WAV thật dẫn clip, speed 0.90–1.10; warning/freeze hoặc error.
- Subtitle synchronization: timing từng unit; không hiện trong silence chèn.
- ZeroTTS-ready abstraction: numeric provider interface, factory, dependency error rõ khi chưa có backend.

## Tests

| Kiểm thử | Kết quả |
| --- | --- |
| Preset resolution + override + clamp | PASS |
| Segmentation | PASS |
| Emotion planner + explicit priority | PASS |
| Seed reproducibility | PASS |
| Edge-TTS thật, đủ 6 preset | PASS |
| Pause assembly / cache / max boundary | PASS |
| Speech metrics / bounded retry | PASS |
| JSON cũ/mới | PASS |
| Subtitle unit timing / pause gaps | PASS |
| Audio duration dẫn clip duration | PASS |
| Slowdown thực không vượt source_end | PASS |
| End-to-end render / full FFmpeg decode | PASS |
| Tổng regression tests | 27/27 PASS |
| pip check | PASS |

Có vài request Edge-TTS trả NoAudioReceived; retry đã thành công, không bỏ unit.
Câu quá ngắn có thể chưa đạt dải speech-rate sau budget; giữ audio và log warning,
không coi đây là lỗi render hoặc âm thầm tăng tốc vượt giới hạn.

## Example

Input:
`Anh ta bước vào căn phòng. Mọi thứ đã biến mất. Nhưng không.`

Detected speech units:
1. Anh ta bước vào căn phòng. → normal
2. Mọi thứ đã biến mất. → suspense
3. Nhưng không. → punchline

Generated audio:
- output/audio/emotion_demo.wav — 23.710s, đủ 6 preset theo thứ tự normal/suspense/excited/serious/punchline/calm.
- output/audio/preview.wav — suspense, 4.334s.
- output/audio/preview_suspense.wav và preview_excited.wav: cùng câu
  “Cánh cửa phía sau bất ngờ bật tung!” để A/B:
  - suspense: +3%, -12Hz; TTS 2.880s, tổng gồm pause 3.480s.
  - excited: +18%, +8Hz; TTS 2.520s, tổng gồm pause 2.670s.

Final video: output/emotion_smoke/final/final_review.mp4.
Input: examples/review.emotion.example.json + test_synthetic.mp4 dài 60s.
Video mới: 28.400s, 47.3333% source, 1280×720/30fps, H.264/AAC48kHz.
Assessment: 14.304s audio TTS; 15.400s trên timeline cuối.
Đúng yêu cầu cũ 40–50% và 10–20s đánh giá, không tắt validator để demo chạy.

Đo lại WAV sau normalize:
- segment 1: -16.00 LUFS, true peak -4.04 dBTP.
- segment 2: -15.99 LUFS, true peak -3.98 dBTP.
Final mix peak đo bằng volumedetect: -4.0 dBFS.
9 subtitle events; kiểm tra toàn bộ event không ăn vào intentional pause quá sai số ASS 10ms.
Đã xem khung mẫu 3s, 18s (pause, không subtitle), 27s; chữ Việt hiển thị đúng.
Không thay thế việc nghe duyệt toàn bộ/đánh giá diễn xuất.

## Useful commands

Chạy từ project với .venv đã activate:

```powershell
python scripts/preview_voice.py --text "Anh ta bắt đầu tiến sâu hơn vào căn nhà." --emotion normal
python scripts/preview_voice.py --text "Nhưng anh ta vẫn chưa biết điều gì đang chờ phía trước." --emotion suspense
python scripts/preview_voice.py --text "Cánh cửa phía sau bất ngờ bật tung!" --emotion excited
python scripts/demo_emotions.py
python scripts/build_review.py --video input/videos/test_synthetic.mp4 --review examples/review.emotion.example.json --output-dir output/emotion_smoke
python scripts/build_review.py --video input/videos/movie.mp4 --review input/scripts/review.v2.json --output-dir output/review_emotion
python -m unittest discover -s tests -v
```

Lệnh phim thật phía trên là lệnh cho lần dựng tiếp; chưa chạy lại phim dài trong task này.
Cần viết/đo lại nếu preset mới làm tổng thời lượng ra ngoài 40–50%.

## Remaining limitations

- Exact intra-unit micro-pause milliseconds: TODO. Hiện giữ dấu câu, dùng prosody native TTS.
- Silence config là pause chèn thêm; không trim pause tự nhiên của Edge ở đầu/cuối chunk.
- Timing subtitle theo unit, trong unit dài vẫn proportional; chưa forced alignment từng từ.
- Heuristic không hiểu toàn bộ ngữ cảnh. Cảm giác tự nhiên/hài hước cần người dùng nghe duyệt.
- Seed tái tạo kế hoạch, không bảo đảm dịch vụ TTS trả waveform bit-identical.
- ZeroTTS stub chưa cài runtime, không giả lập local voice.
- Master final-mix loudnorm riêng: chưa bật; normalize từng narration segment trước mix.
- Bản phim 9:06 trước đây được giữ nguyên, chưa áp dụng emotion presets vào bản đó.

Chi tiết: docs/voice-and-emotion.md; config: config/config.yaml.
