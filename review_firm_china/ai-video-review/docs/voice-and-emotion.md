# Voice and Emotion — narration pipeline

## Kiến trúc

Review narration (string hoặc SpeechUnit[]) → chia câu → heuristic emotion planner
→ preset + override + variation có seed → TTS từng unit → PCM 48 kHz stereo
→ ghép pause → loudnorm hai lượt trên cả segment → đo WAV thật
→ clip duration và subtitle theo timing unit.

Không dùng LLM/API OpenAI/Gemini. Mặc định dùng ZeroTTS / Bảo Trang (`baotrang`)
offline; runtime có trong requirements.txt, model tải một lần bằng setup_zerotts.py.
Edge-TTS cần Internet khi chọn backend này rõ ràng.

## Preset mặc định

| Emotion | Rate | Pitch | Volume | Nghỉ trước | Nghỉ sau |
| --- | --- | --- | --- | --- | --- |
| normal | +24% | 0 Hz | 0% | 0 ms | 100 ms |
| suspense | +22% | 0 Hz | -1% | 0 ms | 160 ms |
| excited | +26% | 0 Hz | +1% | 0 ms | 80 ms |
| serious | +22% | 0 Hz | 0% | 0 ms | 140 ms |
| punchline | +20% | 0 Hz | +1% | 0 ms | 180 ms |
| calm | +22% | 0 Hz | 0% | 0 ms | 160 ms |

Dùng normal để kể; suspense cho bí ẩn; excited cho hành động; serious cho nhận xét;
punchline cho câu chốt; calm cho nhịp mềm/chuyển cảnh.
Đây là điều chỉnh rate/volume/khoảng nghỉ, không phải mô hình diễn xuất cảm xúc.
ZeroTTS giữ cao độ gốc; pitch khác 0 bị từ chối thay vì bỏ qua.

## JSON tương thích cũ và mới

`narration: "Một đoạn lời kể..."` vẫn hợp lệ. Bộ chia câu ưu tiên dấu câu,
nhắm 8–25 token nhưng giữ các câu ngắn hoàn chỉnh/câu chốt.
Dấu thập phân như 1.5 không bị tách. Câu rất dài thiếu punctuation không bị cắt ngang tùy tiện.
Viết rõ unit nếu cần kiểm soát tuyệt đối; heuristic không hiểu ngữ cảnh phim như người viết.

Trong một segment hợp lệ, có thể thay narration bằng:

```json
"narration": [
  {"text": "Anh ta bước vào căn phòng.", "emotion": "normal"},
  {"text": "Nhưng mọi thứ đã biến mất.", "emotion": "suspense", "rate_percent": 6},
  {"text": "Cánh cửa phía sau bất ngờ bật tung!", "emotion": "excited"},
  {"text": "Nhưng không.", "emotion": "punchline", "pause_after_ms": 700}
]
```

ID unit là tùy chọn; tự cấp theo thứ tự, không được trùng trong segment.
Các trường numeric tùy chọn: rate_percent, pitch_hz, volume_percent,
pause_before_ms, pause_after_ms. Null/không có → lấy preset.
Emotion không chỉ định → heuristic; emotion ghi rõ (kể cả normal) → luôn giữ nguyên.
Assessment không có emotion cụ thể → serious.

Thứ tự: preset → jitter cho field tự động → explicit override giữ nguyên.
Không jitter numeric override, không tự retry thay đổi rate nếu unit ghi rõ rate_percent.
Variation mặc định rate ±1%, pitch 0 Hz, pause-after ±15 ms;
seed 42 + segment ID giúp tái hiện kế hoạch. Audio dịch vụ không được đảm bảo bit-identical.

## Config

Các preset nằm trong config/config.yaml; logic không chứa bảng preset.
Config override được merge sâu, ví dụ chỉ thay một field:

```yaml
tts:
  presets:
    suspense:
      rate_percent: 2
      pause_after_ms: 550
  natural_variation:
    enabled: true
    seed: 42
  pause_boundary: max
audio:
  narration:
    loudness_lufs: -16
    true_peak_db: -1.5
video:
  duration_matching:
    enabled: true
    min_speed: 0.90
    max_speed: 1.10
    fallback: freeze
```

Rate clamp -20..30%, pitch -25..20 Hz, volume -10..10%, pause 0..2000 ms;
giá trị ngoài giới hạn có warning. Jitter, retry và speed cũng giới hạn an toàn.
Kiểu dữ liệu sai, NaN hoặc range đảo ngược báo lỗi rõ, không đoán cấu hình.
`tts.rate/pitch` dạng chuỗi được giữ cho direct-provider legacy;
pipeline mới lấy thông số numeric từ preset/unit. Sửa preset để đổi giọng trong build.

## Pause và nhịp đọc

Mặc định khoảng giữa hai unit = max(after trước, before sau), không cộng dồn.
Chọn pause_boundary: additive nếu thực sự muốn cộng. Pause đầu/cuối segment cũng được giữ.
Silence PCM được cache theo sample rate + duration trong output/cache/silence;
khi dùng --output-dir, cache nằm dưới thư mục output đó.

Các pause trên là **silence chèn thêm**. TTS vẫn có nghỉ tự nhiên do dấu câu
ở bên trong/cuối chunk; MVP không cắt bỏ các khoảng nghỉ tự nhiên đó.
TODO: micro_pause có các mốc comma/semicolon/colon/ellipsis trong config, nhưng
chưa ép đúng số ms ở trong unit. Hiện giữ dấu câu để TTS đọc tự nhiên,
và chỉ chia clause dài để tránh unit quá lớn. Không gửi custom SSML.

Metrics dùng token phân tách bởi khoảng trắng chứa chữ/số làm xấp xỉ âm tiết tiếng Việt;
không phải bộ phân tích ngôn ngữ. Debug có nhịp đọc cả segment (kể cả silence chèn)
và nhịp chỉ tính audio TTS (không tính silence chèn; vẫn có nghỉ tự nhiên của TTS).
Vòng rate adaptation đo audio unit, không tính pause được thêm.

Target theo mẫu 1004 là 5.4 tiếng/giây; chấp nhận cả dải, không ép đúng 5.4:
normal 4.9–5.9; suspense 4.7–5.7; excited 5.0–6.1;
serious 4.7–5.7; punchline 4.6–5.6; calm 4.7–5.7.
Dải cảm xúc ưu tiên hơn target chung.
Tối đa 2 lần sinh lại; tổng điều chỉnh không quá ±8 điểm phần trăm so với rate đã resolve,
và luôn trong safe limits. Hết budget/đụng giới hạn thì giữ audio, warning và ghi metadata.
Câu cực ngắn thường không đạt dải do nhịp nghỉ dịch vụ; không cố tăng tốc cực đoan.

## Timeline, subtitle và video

WAV đã ghép/normalize được FFprobe đo thật, làm tròn lên tối đa một frame cho clip.
target_duration không ghi đè thời lượng này.
Subtitles dùng start/end PCM của từng unit, không hiển thị trong silence chèn.
Các unit dài vẫn chia subtitle theo tỷ trọng ký tự trong unit, chưa căn từng từ.

Nếu footage đủ: chọn phần giữa, hoặc điều chỉnh speed nhẹ khi toàn range vừa giới hạn.
Nếu thiếu: thử slowdown tối đa theo min_speed; không đọc quá source_end.
Vẫn thiếu thì log warning và giữ frame cuối (fallback: freeze), không loop.
Mặc định fallback: error để buộc sửa narration/source range thay vì giữ hình.
Chỉ chọn freeze rõ ràng nếu có lý do biên tập; không dùng để đạt quota.
Tốc độ source audio được đổi tương ứng bằng atempo.

Loudnorm hai lượt sau khi ghép segment, không normalize từng unit.
Giữ nguyên timeline PCM, đích -16 LUFS / true peak -1.5 dBTP.
Mix final với background chưa có master loudnorm riêng; cần đo clipping nếu tăng volume.

Chính sách review 40–50% và assessment 10–20s vẫn bật.
Tổng video tính cả khoảng nghỉ hợp lý; không tăng pause để đủ quota.
Assessment kiểm tra cả lời TTS (loại silence chèn) lẫn timeline cuối.
Nếu đổi giọng làm video không đạt tỷ lệ, phải sửa nội dung rồi đo lại.

## Commands

Chạy trong thư mục project, sau khi activate .venv:

```powershell
python scripts/preview_voice.py --text "Anh ta bắt đầu tiến sâu hơn vào căn nhà." --emotion normal
python scripts/preview_voice.py --text "Nhưng anh ta vẫn chưa biết điều gì đang chờ phía trước." --emotion suspense
python scripts/preview_voice.py --text "Cánh cửa phía sau bất ngờ bật tung!" --emotion excited
python scripts/preview_voice.py --text "Nhưng không." --emotion punchline --rate -2 --pitch 0 --pause 700 --no-variation
python scripts/demo_emotions.py
python -m unittest discover -s tests -v
python scripts/build_review.py --video input/videos/test_synthetic.mp4 --review examples/review.emotion.example.json --output-dir output/emotion_smoke
python scripts/build_review.py --video input/videos/movie.mp4 --review input/scripts/review.v2.json --output-dir output/review_emotion
```

Preview mặc định output/audio/preview.wav; --output để giữ nhiều bản.
Các option --voice, --rate, --pitch, --volume, --pause override từng giá trị;
--no-variation tắt jitter, không tắt rate adaptation (rate explicit luôn được giữ).
Demo tạo output/audio/emotion_demo.wav và .tts.json, theo thứ tự 6 hàng preset phía trên.
A/B demo tắt variation/auto-rate để nghe đúng rate/pitch/volume preset; khoảng giữa mẫu
được override thành 1000 ms, normalize cả file sau ghép.

Demo JSON dùng source synthetic 60 giây và assessment riêng.
Mẫu một story segment nguồn 8 giây trong yêu cầu chỉ minh họa cú pháp narration array:
không tự tắt chính sách review để biến nó thành bản review hoàn chỉnh.
Không ghi đè video review thật để test.

## Debug và fallback

- output/debug/segment_001_tts.json: text, emotion, resolved params, attempts,
  start/end từng unit, pause boundary, loudness measurement và speech metrics.
- output/audio/segment_001.wav: audio segment hoàn chỉnh.
- output/audio/segment_001/: unit MP3/WAV từng attempt và assembled.wav.
- output/review_timing.json: kiểm tra tỷ lệ và thời lượng assessment.
- EDL giữ cả tts_duration (đã gồm pause), speech_duration, speech_units.

Nếu Edge-TTS lỗi: retry network hữu hạn, rồi báo segment/unit cụ thể; không skip hoặc tạo giọng im lặng.
Factory create_tts_provider/get_tts_provider cùng contract numeric.
ZeroTTS đã chạy cục bộ với Mai Chi, Bảo Trang, Kim Oanh: chọn
`config/zerotts.maichi.yaml`, `config/zerotts.baotrang.yaml` hoặc
`config/zerotts.kimoanh.yaml` qua `--config`. Model tải một lần bằng
`python scripts/setup_zerotts.py`; tạo lời đọc sau đó chạy offline.
Tempo và âm lượng được xử lý qua FFmpeg. ZeroTTS không hỗ trợ `pitch_hz`,
nên ba cấu hình để pitch bằng 0 và tắt jitter cao độ. Emotion chỉ thay đổi
nhịp/âm lượng/khoảng nghỉ, không phải điều khiển diễn xuất của model.
Thiếu model/runtime/voice báo lỗi, không âm thầm đổi sang Edge.
Có thể thay HeuristicEmotionPlanner qua interface EmotionPlanner; chưa gọi LLM planner.

Bản movie review 9:06 trước nâng cấp giữ nguyên. Chưa tự render lại phim thật với các preset mới.
