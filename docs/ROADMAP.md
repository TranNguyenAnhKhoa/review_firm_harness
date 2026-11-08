# Việc cần cải tiến

Ghi ngày 2026-11-08, sau lần dựng lại bản Linux. Mỗi mục có căn cứ từ lần chạy thử và ước lượng thời gian làm.

Thứ tự đề xuất: chạy thử 1 tập thật, rồi mục 3, rồi mục 2. Hai mục này sửa đúng thứ người xem thấy trên video.

## 0. Chạy thử 1 tập phim thật (làm trước)

Flow mới mới được thử trên phim tổng hợp 90 giây: agy READ 189 s / 95k token, agy WRITE 347 s / 157k token,
MEASURE + RENDER + QC 50 s, QC đạt (41,9 s = 46,6% nguồn). Chưa biết agy xử lý ra sao khi một phiên phải xem
48 phút phim (5 proxy 10 phút). Kết quả lần chạy đó quyết định mục 1 có gấp không.

## Nên làm

### 1. Tách READ theo từng đoạn phim (khoảng 2-3 giờ)

- Hiện tại: một phiên agy xem hết mọi proxy rồi mới ghi `timeline.md`. Phim dài thì ngữ cảnh rất nặng, và
  phiên lỗi giữa chừng là mất toàn bộ.
- Đề xuất: mỗi proxy 10 phút chạy một phiên riêng, chạy song song, ghi timeline từng đoạn; thêm một bước ghép
  (nối bảng D/E, gộp bảng nhân vật, viết lại mục B/G/H). Đoạn nào lỗi chỉ chạy lại đoạn đó.
- Căn cứ: timeline của bản Windows chỉ có 10 dòng cho 48 phút và không có bảng shot. Agent xem cả phim một
  lượt có xu hướng tóm tắt quá thưa.
- Chỗ sửa: `harness/pipeline/stages.py` (hàm `read`), `prompts/read.md` (thêm prompt cho một đoạn và prompt ghép).

### 2. Storyboard để duyệt WRITE (khoảng 1-2 giờ)

- Hiện tại: WRITE chọn mốc shot chỉ dựa vào chữ trong timeline, không xem lại khung hình ở mốc nó chọn. Người
  duyệt chỉ thấy JSON.
- Đề xuất: sau WRITE, harness cắt 1 ảnh cho mỗi shot (giữa khoảng `source_start`-`source_end`), xếp cạnh câu
  kể tương ứng. Dashboard hiện storyboard này ở ô WRITE để duyệt bằng mắt. Tuỳ chọn: một lượt agy tự soát hình
  có khớp câu không và ghi cảnh báo.
- Căn cứ: README bản cũ ghi "Timeline hình vẫn là bản đối chiếu mẫu (partial), cần xem/nghe duyệt".
- Chỗ sửa: `harness/pipeline/stages.py` (sau `write`), `harness/pipeline/materials.py` (dùng lại `zoom_frames`,
  `_sheet`), `harness/monitor/static/index.src.html`.

### 3. Phụ đề cứng bị cắt mất một nửa (khoảng 1 giờ)

- Căn cứ: khung hình kiểm tra của video cuối bản thử còn nửa dòng phụ đề vàng ở mép dưới. Chế độ
  `fit_mode: cover` crop ngang qua giữa dải phụ đề. Phim Trung có phụ đề Việt cứng sẽ gặp lỗi này ở hầu hết shot.
- Đề xuất: dò dải phụ đề (giống cách `_source_bars` trong `harness/video/picture_style.py` đang dò viền đen),
  rồi hoặc crop hẳn dải đó, hoặc che mờ, hoặc dịch vùng crop để giữ trọn dòng. Thêm tuỳ chọn
  `render.picture_style.hardsub: crop | blur | keep`.
- Thêm test với video tổng hợp có dòng chữ sát đáy.

### 4. Hỗ trợ phim nhiều tập (khoảng 3-4 giờ)

- Bảng nhân vật dùng chung: từ tập 2, READ nhận sẵn tên và nhận diện nhân vật của các tập trước (ví dụ
  `series/<ten-phim>/characters.md`), để tên gọi nhất quán thay vì NV01, NV02 mỗi tập.
- Hàng đợi: nhiều job chạy cùng lúc đang tranh CPU (TTS, render). Thêm giới hạn số run song song; job thừa
  xếp hàng và tự chạy khi có chỗ. Dashboard hiện vị trí trong hàng.

### 5. Bỏ bớt duyệt tay khi kết quả sạch (khoảng 30 phút)

- Đề xuất: READ tự duyệt khi `analysis_status: complete`, độ phủ từ 95% trở lên và không có cảnh báo. Giữ cổng
  WRITE vì lời kể cần người đọc. Bật/tắt bằng một khoá cấu hình (ví dụ `gates_auto: [read]`).
- Mỗi tập bớt 1 lần chờ người.

## Để sau

- Tăng `measure.workers` từ 2 lên 4-6 trên máy nhiều lõi: 4 segment đo mất 38 s với 2 luồng trên máy 24 lõi.
- Ước tính thời lượng trước TTS đã khớp số đo thật (ước tính 42 s, đo 41,9 s), chưa cần sửa.
