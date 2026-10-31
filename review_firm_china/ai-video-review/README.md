# AI Video Review — local MVP

Python 3.11 + FFmpeg dựng review từ video nguồn và review.json.
READ dùng Antigravity Desktop (gửi qua giao diện) hoặc Gemini Pro thủ công;
WRITE dùng ChatGPT Pro thủ công; không cần API key.
Flow mặc định dùng giọng Bảo Trang (`baotrang`) của ZeroTTS, tạo lời đọc offline.
Không tích hợp Gemini/OpenAI API hoặc Hermes.
Flow đã lấy `SrcVideo/1004.mp4` làm mẫu: lời kể vào tình huống ngay, shot ngắn
cắt thẳng theo timing Bảo Trang, 1920×1080/30 fps có viền đen và watermark nhỏ,
không có subtitle narration lớn mặc định. [Hướng dẫn flow, schema shots và số đo](docs/reference1004-flow.md).

Moana: bản biên tập hiện tại là `input/scripts/review.moana.v3.json`.
Đã dựng bản kiểm tra `output/moana_render_v3/final/final_review.mp4`:
53:15.56, bằng 46.05% nguồn, đánh giá cuối có 14.40 giây lời nói.
Giải mã toàn bộ H.264/AAC PASS; 39 test PASS. Timeline hình vẫn là bản đối chiếu
mẫu (`partial`), cần xem/nghe duyệt trước khi công bố.
Audio nghe riêng: `output/moana_v2/listening/moana_narration.mp3`.
Xem [lệnh dựng từ cache, kết quả và giới hạn kiểm chứng Moana](docs/moana-revision.md).
`review.moana.json` và v2 được giữ nguyên làm bản gốc/nháp, không phải bản bàn giao mới nhất.

## Architecture

    Antigravity Desktop READ → data/timeline/<job>/timeline.md
        hoặc Gemini Pro (manual) → timeline.md / analysis.json
    ChatGPT Pro (manual) → review.json
    Local Python + PySceneDetect + ZeroTTS (Bảo Trang) + optional Demucs + FFmpeg
        → output/final/final_review.mp4

`shots` trong review.json hỗ trợ montage; `speech_unit_id` gắn hình với lời đọc
đã đo. Cả build_review và render_measured_review dùng cùng bố cục. JSON cũ
vẫn chạy một range/đoạn, chưa tự trở thành nhịp cắt của mẫu.

## System detected (lần setup ban đầu)

- Windows 10 Pro 10.0.19045 x64.
- Intel Core i7-6820HQ @ 2.70 GHz, RAM 15.82 GiB.
- Quadro M1000M, 2048 MiB VRAM, driver 528.79.
- NVIDIA-SMI báo CUDA tối đa driver hỗ trợ: 12.0; không thấy nvcc trên PATH.
- Python 3.11.9, pip 26.2.1, Git 2.54.0.windows.1.
- FFmpeg/FFprobe 9.0.2 full build, có libx264/libass.
- PyTorch 2.5.1+cpu; CUDA available: false.
- PySceneDetect 0.7.1, Edge-TTS 7.2.8, Demucs 4.1.0, Pydantic 2.13.5.

PyTorch 2.14 ban đầu lỗi DLL WinError 193. Đã thay bằng CPU 2.5.1
và đồng bộ SymPy 1.13.1; pip check sạch. Không thay driver.
CUDA hiển thị trong nvidia-smi không chứng minh CUDA Toolkit đã cài.

## Khởi chạy

    cd D:\workplace_make_firm\review_firm_china\ai-video-review
    .\.venv\Scripts\Activate.ps1
    python scripts\setup_zerotts.py  # Tải model một lần khi cài mới
    python scripts\check_environment.py

Nếu Activate.ps1 bị chặn, gọi .venv\Scripts\python.exe thay python;
không cần đổi execution policy. Mọi lệnh dưới đây chạy từ thư mục project.
Đường dẫn tương đối trong CLI/config tính từ thư mục đang chạy.

Setup đã chuyển sang user `khoatna`: `.venv` dùng Python 3.11.17 tại
`C:\Users\khoatna\AppData\Roaming\uv\python\cpython-3.11.17-windows-x86_64-none`.
Pipeline tự dò FFmpeg/FFprobe trong tool store `%LOCALAPPDATA%\hermes\tools`
nếu không có trên PATH hoặc trong Winget; không phụ thuộc thư mục user cũ.
Kiểm tra lại ngày 2026-10-12: Python 3.11.17, FFmpeg/FFprobe 9.0.1,
environment PASS, `pip check` sạch, 51 regression tests PASS và tạo được
lời đọc Bảo Trang offline tại `output/user_migration_check/baotrang.wav`.
Hermes giữ runtime Python 3.14 riêng; không dùng runtime đó cho `.venv` dựng phim.

Windows khóa đổi tên thư mục cũ nên bản D:\workplace_make_firm\ai-video-review
được giữ nguyên. Bản bàn giao và các sửa đổi cuối cùng nằm trong review_firm_china.

## Workflow

### Step 1 — Antigravity READ (ưu tiên)

Mở Antigravity Desktop đã đăng nhập. Gửi video local bằng lệnh:

```powershell
python scripts/antigravity_handoff.py --job moana --video "input/videos/Hành Trình Của Moana - Moana (2026) - Phimmoichill.mp4" --send
python scripts/antigravity_handoff.py --job moana --check
```

Bỏ `--send` nếu chỉ muốn chuẩn bị yêu cầu. Script tạo
`data/handoff/moana/request.md` và manifest; yêu cầu Antigravity đọc video thật,
trả file UTF-8 tại:

    D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\moana\timeline.md

[Prompt READ chi tiết](prompts/antigravity_read.md) gồm timeline, bằng chứng,
nhân vật, lựa chọn clip, chất liệu hài hước, đánh giá cuối và ngân sách 40–50%.
Mỗi phim dùng `--job` khác để bảo toàn timeline cũ.

Handoff điều khiển giao diện Desktop qua endpoint debug loopback sẵn có,
không dùng Gemini/OpenAI API, không đọc token và không tự chấp nhận hộp thoại quyền.
Yêu cầu app đang mở và giao diện tương thích; cập nhật app có thể đổi selector.
Không tự gửi lại job đã gửi hoặc có trạng thái gửi chưa chắc chắn.
Nếu có bản nháp đang mở, script dừng để bảo toàn bản nháp.

`UI_SUBMITTED` chỉ xác nhận gửi. `--check` trả exit 2 khi chưa có file hoặc
`partial/blocked`; exit 0 chỉ khi metadata hợp lệ và file tự khai `complete`.
Đây **không** phải kiểm định nội dung: vẫn phải đọc phạm vi/bằng chứng/timestamp
trước khi viết review. Video dài/lớn có thể vượt khả năng của công cụ Antigravity;
yêu cầu phải báo thiếu, không kể lại phim theo trí nhớ. Không tự render khi thiếu timeline.

### Step 1b — Gemini READ thủ công (dự phòng)

1. Upload video `input/videos/movie.mp4` vào Gemini Pro.
2. Mở [prompt Gemini chi tiết](prompts/gemini_read.md), copy toàn bộ nội dung
   và gửi cùng video. Prompt hiện điền thông số phim 1193.033 giây;
   nếu dùng video khác, thay thông số ở phần đầu.
3. Có thể đính kèm thêm `data/timeline/movie.scenes.json` để đối chiếu timestamp.
4. Yêu cầu Gemini xuất **file Markdown UTF-8 tên timeline.md để tải xuống**.
   Nếu phiên Gemini không hỗ trợ file đính kèm, dùng khối Markdown đầy đủ mà
   Gemini trả lại và lưu thành `timeline.md` (không phải `timeline.md.txt`).
5. Đặt file vào thư mục:

       D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\

   Đường dẫn đầy đủ:

       D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\timeline.md

   Gemini không tự ghi vào ổ D:; bạn tải file rồi copy vào thư mục trên.
   Nếu đã có timeline.md, giữ bản cũ với tên khác trước khi thay thế nếu cần.

Prompt yêu cầu diễn biến chi tiết, nhân vật, bằng chứng, đoạn hình gợi ý,
chất liệu hài hước, nhận xét tác phẩm và các điểm chưa chắc.
Ngân sách review 40–50% đã bao gồm 10–20 giây đánh giá cuối.

Có thể lấy timestamp scene local:

    python scripts\detect_scenes.py input\videos\movie.mp4 --threshold 27

Output data/timeline/scenes.json; không split thành file video.
Video không có cut vẫn trả một scene toàn video.

### Step 2 — ChatGPT WRITE

Đưa timeline vào ChatGPT Pro, yêu cầu JSON theo
[examples/review.example.json](examples/review.example.json).
File đầu vào là `data/timeline/<job>/timeline.md` từ Antigravity đã kiểm tra,
hoặc `data/timeline/timeline.md` do Gemini xuất thủ công.
Với Moana, dùng `data/timeline/moana/timeline.md`, lưu kịch bản riêng
`input/scripts/review.moana.json` và output riêng `output/moana`.
Pydantic schema: src/pipeline/schema.py. Hướng dẫn viết mới:
[prompts/write_review.md](prompts/write_review.md) và
[quy tắc biên tập](docs/editorial-guidelines.md).

Mỗi segment có id, narration, source_start, source_end,
visual_intent, target_duration, keep_original_audio và section.
Narration hỗ trợ cả string cũ và mảng SpeechUnit mới (text, emotion, override numeric).
Các đoạn kể dùng section="story"; đúng một đoạn cuối dùng section="assessment".
ID duy nhất, narration không rỗng, timestamp hữu hạn,
0 <= source_start < source_end <= thời lượng video.

--video quyết định video được dùng; source_video trong JSON là tham chiếu.
target_duration là ý định; TTS thật quyết định thời lượng edit.
visual_intent chỉ là metadata, chưa có AI best-shot selection.

### Step 3 — Chuẩn bị input

Copy movie.mp4 vào input/videos/ và review.json vào input/scripts/.
Không cần API key.

### Step 4 — Local EDIT

    python scripts\build_review.py --video input\videos\movie.mp4 --review input\scripts\review.json

Validate → probe → TTS → đo audio → chọn/cắt clip → background →
ASS subtitle → FFmpeg render → validate duration/codec/kích thước.

### Step 5 — Output

- output/final/final_review.mp4: video hoàn chỉnh.
- output/audio/: TTS MP3 và PCM WAV.
- output/clips/: clip đã cắt.
- output/subtitles/review.ass: subtitle.
- data/edl/review.json: TTS duration, edit duration, offset timeline.
- output/tmp/: concat, Demucs nếu bật, file trung gian.

## Editing và config

### Yêu cầu biên tập (cập nhật 2026-10-03)

- Video review dài 40–50% video gốc, đã tính phần đánh giá cuối; mục tiêu 45%.
- Đoạn đánh giá tác phẩm ở cuối dài 10–20 giây, ưu tiên 15 giây.
- Giọng văn hài hước, hợp khán giả trẻ và tác phẩm; không bịa tình tiết để pha trò.
- Pipeline kiểm tra bằng TTS thực tế trước khi cắt clip và kiểm tra video xuất cuối.
  Không đạt thì báo lỗi, lưu output/review_timing.json để chỉnh lời kể.
  Video mới chỉ thay thế final_review.mp4 sau khi vượt kiểm tra.
- Chất lượng câu đùa/đánh giá do người viết kiểm tra; code chỉ xác nhận nhãn và thời lượng,
  không hiểu nội dung để đảm bảo giọng văn đúng yêu cầu.

In ngân sách thời lượng theo video:

    python scripts/review_brief.py --video input/videos/movie.mp4

Đo TTS, chưa render:

    python scripts/build_review.py --video input/videos/movie.mp4 --review input/scripts/review.json --tts-only --output-dir output/timing_check

Thời lượng dùng cả audio và frame thực tế, không lấy target_duration hoặc số từ làm chuẩn.
Với video 1193.033 giây: review 477.213–596.517 giây, mục tiêu 536.865 giây.
Bản review cũ 287 giây chưa đạt; cần viết lại dài hơn và thêm assessment riêng trước khi dựng.

Sửa [config/config.yaml](config/config.yaml), hoặc dùng
--config examples/config.example.yaml.

MP3 được decode thành WAV PCM 48 kHz stereo trước khi đo bằng FFprobe.
Timeline làm tròn lên theo frame; thêm tối đa một frame mỗi segment.
Narration/subtitle dùng cùng offset để tránh tích lũy sai lệch.

Source dài hơn lời đọc: lấy phần giữa range.
Source ngắn hơn: thử slowdown trong giới hạn duration_matching; vẫn thiếu thì
warning và giữ frame cuối (hoặc fallback: error). Không vượt source_end, không loop.
choose_centered_range là interface để thay AI best-shot selection sau này.
Video không có audio vẫn chạy nhờ bổ sung silence.

Mặc định giữ kích thước/aspect nguồn; chiều lẻ được làm tròn xuống số chẵn
để encode yuv420p. Video dọc giữ chiều dọc.
render.keep_source_resolution: false dùng canvas 1920x1080 hoặc 1080x1920
theo hướng nguồn, padding để giữ aspect. Codec H.264/libx264 + AAC.

Volume mặc định narration 1.0, background 0.18; có fade ngắn ở biên audio.
keep_original_audio: false tắt background segment.
Nếu tăng volume nhiều, cần tự kiểm tra clipping.

ASS dò font Unicode phổ biến: Arial → Segoe UI → Tahoma trên Windows,
DejaVu Sans/libass fallback ở hệ khác.
Config: font_size, max_chars_per_line, position (bottom/top).
Speech unit dài được chia tối đa hai dòng/event, timing theo độ dài chữ trong unit;
chưa có forced alignment từng từ.

## TTS provider và ZeroTTS

Contract src/audio/tts.py:

    class TTSProvider:
        def synthesize(self, text: str, output_path: str, voice: str | None = None,
                       *, rate_percent: int = 0, pitch_hz: int = 0,
                       volume_percent: int = 0) -> str:
            ...

`config/config.yaml` mặc định `tts.provider: zerotts`, `tts.voice: baotrang`.
Các lệnh build_review, measure_review, preview_voice và test_tts dùng Bảo Trang
ngay khi chạy với cấu hình mặc định. Các cấu hình phim kế thừa cùng giọng này.
Model được ghim revision và tạo lời đọc offline; cao độ và jitter cao độ bằng 0.
Cache đo lời đọc có chữ ký provider/voice/config, nên audio giọng cũ không được
tái dùng cho lần đo với Bảo Trang. Video đã xuất có giọng cũ cần dựng lại để đổi tiếng.
Edge-TTS vẫn có thể chọn rõ `provider: edge` và voice ID, cần Internet.

ZeroTTSProvider chạy ONNX cục bộ, đã tích hợp Mai Chi (`maichi`), Bảo Trang
(`baotrang`) và Kim Oanh (`kimoanh`). Chọn một trong ba file cấu hình:

| Giọng | Cấu hình |
|---|---|
| Mai Chi | `config/zerotts.maichi.yaml` |
| Bảo Trang | `config/zerotts.baotrang.yaml` |
| Kim Oanh | `config/zerotts.kimoanh.yaml` |

Cài từ checkout ZeroTTS có sẵn trong workspace và tải model một lần:

    python -m pip install ../../ZeroTTS
    python scripts/setup_zerotts.py

Hoặc cài bản đóng gói: `python -m pip install -r requirements-zerotts.txt`.
Model và voice packs nằm trong `data/models/zerotts/`, không đưa vào Git.
Các cấu hình ghim revision model và bật `local_files_only: true`, nên sau khi
tải xong việc tạo lời đọc chạy offline. Dùng cùng `--config` với build_review,
measure_review hoặc preview_voice:

    python scripts/preview_voice.py --config config/zerotts.maichi.yaml --text "Câu chuyện bất ngờ bắt đầu từ đây." --output output/zerotts_preview/maichi.wav
    python scripts/preview_voice.py --config config/zerotts.baotrang.yaml --text "Câu chuyện bất ngờ bắt đầu từ đây." --output output/zerotts_preview/baotrang.wav
    python scripts/preview_voice.py --config config/zerotts.kimoanh.yaml --text "Câu chuyện bất ngờ bắt đầu từ đây." --output output/zerotts_preview/kimoanh.wav
    python scripts/test_zerotts.py

ZeroTTS không có điều khiển emotion/cao độ gốc. Adapter thay đổi tốc độ bằng
FFmpeg `atempo` (giữ cao độ) và âm lượng bằng `volume`; pipeline vẫn quản lý
khoảng nghỉ, đo thời lượng và chuẩn hóa loudness. Ba cấu hình đặt pitch bằng 0
và tắt jitter cao độ. Yêu cầu `pitch_hz` khác 0 báo lỗi rõ ràng. Emotion presets
điều chỉnh nhịp/âm lượng/khoảng nghỉ, không bảo đảm diễn xuất cảm xúc.
Adapter chuẩn hóa số/ngày tiếng Việt, chia văn bản dài, dùng seed ổn định và tái
sử dụng model giữa các giọng. Voice ID có thể nhập `maichi` hoặc `Mai Chi`,
`baotrang` hoặc `Bảo Trang`, `kimoanh` hoặc `Kim Oanh` khi chọn provider ZeroTTS.
Thiếu model/voice/runtime báo lỗi, không âm thầm chuyển sang Edge.

## Voice and Emotion

Đã nâng cấp narration theo speech unit, giữ JSON narration string cũ.
Sáu preset: normal (kể), suspense (bí ẩn), excited (hành động), serious (nhận xét),
punchline (câu chốt), calm (nhịp mềm). Có override numeric, jitter có seed, retry
nhịp đọc hữu hạn, pause boundary max, loudnorm sau concat và subtitle theo unit timing.

Hướng dẫn, bảng preset, JSON/config và giới hạn:
[docs/voice-and-emotion.md](docs/voice-and-emotion.md).
Ví dụ đầy đủ: [examples/review.emotion.example.json](examples/review.emotion.example.json).

    python scripts/preview_voice.py --text "Nhưng anh ta vẫn chưa biết điều gì đang chờ phía trước." --emotion suspense
    python scripts/demo_emotions.py
    python scripts/build_review.py --video input/videos/test_synthetic.mp4 --review examples/review.emotion.example.json --output-dir output/emotion_smoke

**TTS duration drives video clip duration**: đo WAV đã ghép/normalize, bao gồm pause,
không dùng target_duration thay thế. Subtitle không hiển thị trong intentional pause.
Micro-pause trong unit hiện do dấu câu của TTS; ép đúng số ms là TODO.
Tỷ lệ review 40–50% và assessment 10–20s vẫn kiểm tra; không tăng pause để lách giới hạn.

## Demucs

    python scripts\test_demucs.py
    python scripts\test_demucs.py input\audio\test.wav

Không input: kiểm tra runtime. Có input: tách thật và kiểm tra duration stems.
Model htdemucs; output ở output/audio/demucs/htdemucs/test/:
vocals.wav và no_vocals.wav. Model tải ở lần đầu vào cache người dùng.

audio.use_demucs: true tách audio của video concat rồi ưu tiên no_vocals.
Nếu CUDA thất bại, thử CPU. Nếu Demucs vẫn thất bại, cảnh báo và
fallback audio gốc giảm volume. Mặc định tắt vì CPU chậm với phim dài.

Demucs tách nguồn âm nhạc, không phân biệt dialogue/SFX hoàn hảo:
có thể mất tiếng động hoặc còn lời thoại.
TODO: đánh giá chất lượng trên clip phim thật trước khi xử lý cả phim.

## Smoke test

    python scripts\smoke_test.py --demucs

Smoke test dùng test pattern + sine wave 60 giây, không download video Internet.
Nguồn 10 giây chỉ cho phép review 4–5 giây, không chứa được assessment tối thiểu 10 giây;
vì vậy bài end-to-end mới dùng nguồn 60 giây. Test FFmpeg riêng vẫn mặc định 10 giây.
Demo mới xuất vào output/editorial_smoke/ để không ghi đè bản phim thật.
TTS cần Internet; Demucs cần model cache hoặc Internet ở lần đầu.
Kết quả: output/smoke_results.json.

Kiểm thử ngày 2026-10-02: environment, FFmpeg/FFprobe, SceneDetect,
Vietnamese TTS, Demucs import + separation, renderer và end-to-end PASS.
5 regression tests PASS: schema/range, known cut/single scene,
video dọc không audio, freeze-frame trong range, concat/ASS/final decode.

Lệnh riêng:

    python scripts\test_ffmpeg.py --duration 60
    python scripts\detect_scenes.py input\videos\test_synthetic.mp4
    python scripts\test_tts.py
    python -m unittest discover -s tests -v
    python scripts\build_review.py --video input\videos\test_synthetic.mp4 --review examples\review.example.json --output-dir output/editorial_smoke

## Tái tạo environment

Cài Python 3.11 x64 và FFmpeg/FFprobe trước; chỉ cài packages trong .venv.

    py -3.11 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
    .\.venv\Scripts\python.exe -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m pip check

requirements-lock.txt lưu toàn bộ version đã kiểm thử trên Windows.
Muốn cài lock, cài PyTorch CPU trước rồi -r requirements-lock.txt.

Nếu FFmpeg không trên PATH, mở terminal mới hoặc set FFMPEG_BINARY và
FFPROBE_BINARY thành đường dẫn .exe. Project tự dò Winget khi có thể.
Trên máy có Hermes, project cũng tự dò bản FFmpeg trong tool store của user hiện tại.
.env.example chỉ là tài liệu mẫu, không tự load .env.
Subprocess dùng argument list, không shell=True; lỗi trả command và stderr.

## Git và giới hạn MVP

Repo đã init, chưa commit. Source video, generated audio/output, .venv,
model weights, .env và file tạm được ignore; giữ thư mục bằng .gitkeep.

Chạy một build mỗi lần; output cùng tên sẽ bị ghi đè.
MVP encode CPU, giữ artifact để debug; chưa có TTS cache/resume,
parallel rendering hoặc tự kiểm chứng timeline của Gemini.

Bước tiếp theo: Gemini timeline → ChatGPT review.json → local editor
với một đoạn phim thật do bạn cung cấp.
