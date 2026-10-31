# Kiểm thử video review v2

Ngày chạy: 2026-10-03. Kết quả: PASS cho luồng local end-to-end.

## Đầu vào và phạm vi

- Video thật: `input/videos/movie.mp4`, 1193.033333 giây, 720×1280.
- Timeline: bản phân tích thủ công người dùng đã cung cấp; không chạy lại Gemini.
- Kịch bản mới: `input/scripts/review.v2.json`; bản dễ đọc: `input/scripts/review.v2.narration.md`.
- 29 segment kể chuyện và đúng 1 segment đánh giá cuối.
- Không gọi Gemini API hoặc OpenAI API. Edge-TTS cần kết nối mạng, không cần API key.
- Config: `config/review.movie.yaml`, giọng đọc tốc độ mặc định; nền gốc volume 0.08; Demucs tắt.

## Kết quả đo từ file xuất

| Hạng mục | Kết quả |
| --- | --- |
| Video | `output/review_v2/final/final_review.mp4` |
| Thời lượng | 546.566667 giây, tức 09:06.567 |
| Tỷ lệ nguồn | 45.8131933%, đạt 40–50% |
| Đánh giá cuối bắt đầu | 531.733333 giây, tức 08:51.733 |
| TTS đánh giá cuối | 14.832 giây, đạt 10–20 giây |
| Đánh giá trên timeline cuối | 14.833334 giây |
| Định dạng | H.264 / AAC, 720×1280, 30 fps, audio 48 kHz |
| Dung lượng | 128257297 byte |
| FFmpeg giải mã toàn bộ với -xerror | PASS, stderr rỗng |
| Âm lượng trung bình / đỉnh | -21.5 dB / -5.1 dB; đỉnh dưới 0 dBFS |
| Bộ kiểm thử local | 13/13 PASS |
| Kiểm tra môi trường | PASS; PyTorch CPU, CUDA không khả dụng trong env |
| Phụ đề | 168 lượt hiển thị, ASS burn-in |

Báo cáo máy đọc: `output/review_v2/review_timing.json`.
EDL: `output/review_v2/edl/review.json`.

Đã xem các khung hình ở 13s, 275s, 538s và 544s:
dấu tiếng Việt hiển thị đúng, chữ nằm trong khung, không chồng chữ Trung ở các mẫu đã xem.
Ảnh kiểm tra nằm tại `output/review_v2/qa/`.
Đây là kiểm tra khung mẫu, không phải chứng nhận mọi khung hình hoặc nghe duyệt toàn bộ lời đọc.

## Chạy lại

Tại thư mục project, PowerShell:

```powershell
.\.venv\Scripts\python.exe -u scripts/build_review.py --video input/videos/movie.mp4 --review input/scripts/review.v2.json --config config/review.movie.yaml --output-dir output/review_v2
```

Lệnh này dựng lại các artifact v2. Muốn giữ cả bản v2, đổi `--output-dir` sang thư mục mới.

## Bảo toàn và giới hạn MVP

- Video cũ `output/final/final_review.mp4` giữ nguyên SHA256:
  `72180A155619ED8C6182FD21D4F7080A431E48C3667461B65A28DBB5F79AF1BC`.
- Kịch bản `input/scripts/review.json` cũ và video nguồn không bị ghi đè.
- Clip vẫn dùng chọn giữa cửa sổ thời gian, chưa có AI chọn shot.
- Cảnh mở đầu giữ hình cuối thêm 0.3 giây vì narration dài hơn cảnh ngắn.
  Các segment còn lại không cần kéo hình quá cửa sổ nguồn.
- Tổng thời lượng đạt bằng kịch bản và TTS thật, không giảm tốc giọng hoặc chèn khoảng im lặng để đạt tỷ lệ.
- Phụ đề canh theo thời lượng đoạn và độ dài chữ; chưa có căn chỉnh từng từ.
- Chữ Trung đã dính vào video nguồn còn nguyên.
- Độ hài hước và mức hợp thị hiếu cần người dùng xem/nghe duyệt; không có kiểm thử tự động kết luận gu hài.
- Demucs import/runtime được kiểm tra môi trường; bản render này không dùng tách giọng.

