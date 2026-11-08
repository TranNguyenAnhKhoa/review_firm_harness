# Flow review theo mẫu 1004

Flow mặc định lấy video mẫu `1004.mp4` (bản Windows cũ, không có trong repo) làm tham chiếu
biên tập và dùng Bảo Trang cho lời đọc. Số đo nằm ở `examples/reference/1004.analysis.json`.

## Những gì quan sát và đo được

| Thành phần | Mẫu | Flow của chúng ta |
|---|---|---|
| Khung hình | 1920×1080, 30 fps | Cùng kích thước và fps |
| Viền đen | Khoảng 115 px trên/dưới | 116 px trên/dưới, kích thước chẵn |
| Cắt cảnh | Detector phát hiện 81 shot/126,57 giây, trung vị 1,57 giây | Hard cut, nhắm 1–2 giây/shot; dùng timestamp đã READ |
| Lời đọc | ASR ước lượng 5,04 tiếng/giây cả nghỉ; 5,57 trong đoạn đọc | Bảo Trang, mục tiêu 5,4; dải kể 4,9–5,9, retry hữu hạn |
| Khoảng nghỉ | Trung vị giữa đoạn ASR 0,36 giây | Pause chèn 80–180 ms cộng nghỉ tự nhiên của ZeroTTS; phải đo lại |
| Lời kể | Vào tình huống ngay, kể nối hành động/phản ứng, đưa thoại vào lời kể | Prompt WRITE và hướng dẫn biên tập đã cập nhật |
| Chữ | Không thấy phụ đề narration lớn trong các frame kiểm tra; watermark nhỏ góc phải | Subtitle narration mặc định tắt; watermark “Review Phim” |
| Âm thanh nền | Chưa nghe trực tiếp hoặc đo được stem riêng | Giữ nguồn nhỏ ở gain 0,08, narration -16 LUFS, limiter cuối |

Đây là dựng theo đặc điểm quan sát được. Không có project CapCut gốc, curves EQ,
stem nhạc/thoại hay thông số nén âm thanh để khẳng định sao chép chính xác toàn bộ.
File mẫu kết thúc giữa câu, chưa xác minh cấu trúc kết thúc hoặc tỷ lệ cả phim.
Quy tắc review 40–50% nguồn và assessment 10–20 giây của project vẫn áp dụng.

## Flow làm một phim mới

1. READ bằng agent (agy xem video proxy, hoặc claude/codex xem sheet ảnh): timeline thật và shot cụ thể cho hành động,
   gương mặt phản ứng, vật thể quan trọng, câu thoại đáng giữ. Đánh dấu khoảng thiếu.
2. WRITE: hook ngay câu đầu; diễn biến theo nguyên nhân → hành động → hậu quả;
   pha nhận xét ngắn đúng tình huống. Không chèn intro dài, không bịa câu thoại.
3. Mỗi đoạn narration có `shots` theo thứ tự lời kể. Thường 5–10 shot cho đoạn
   8–15 giây. Lựa chọn thời gian nguồn dựa trên READ, không tự chọn nhân vật bằng
   detector cảnh hay lấy ảnh ở giữa một khoảng dài rồi coi là đã đọc phim.
4. TTS bằng Bảo Trang, đo PCM thật và thử chỉnh rate trong giới hạn. Nếu lệch
   ngân sách, sửa lời kể rồi đo lại. Không giữ frame/lặp clip để đạt tỷ lệ.
5. Dựng montage theo thời lượng đo, hard cut; đặt canvas/viền đen/watermark,
   giảm âm thanh gốc. Thiếu footage báo lỗi thay vì freeze mặc định.
6. Xem `review_timing.json`, `flow_report.json` và EDL; nghe/xem duyệt nội dung,
   đồng bộ hành động, tiếng nền, phụ đề/logo có sẵn trước khi công bố.

## Shot gắn với câu kể

Đặt narration dạng speech unit có ID, rồi gắn shot với `speech_unit_id`:

```json
{
  "id": 1,
  "section": "story",
  "source_start": 10,
  "source_end": 30,
  "narration": [
    {"id": "u1", "text": "Câu kể về hành động đã được xác nhận ở timeline.", "emotion": "normal"},
    {"id": "u2", "text": "Câu kể về phản ứng tiếp theo của nhân vật.", "emotion": "normal"}
  ],
  "shots": [
    {"source_start": 10, "source_end": 14, "speech_unit_id": "u1", "weight": 1},
    {"source_start": 16, "source_end": 20, "speech_unit_id": "u1", "weight": 1},
    {"source_start": 24, "source_end": 30, "speech_unit_id": "u2", "weight": 1}
  ],
  "keep_original_audio": true
}
```

Timestamp/nội dung trên chỉ minh họa schema. Shot phải nằm trong source_start/
source_end của đoạn. Tối đa 24 shot/đoạn. Có anchor thì phải gắn tất cả shot,
phủ mọi unit theo đúng thứ tự, dùng ID unit rõ ràng. Cut tại ranh giới unit dùng
timing PCM thật; trong một unit chia thời lượng theo weight, không forced-align
từng từ. Frame được phân bổ sao cho tổng montage bằng thời lượng narration đã
làm tròn frame; không cắt cụt lời đọc.

Nếu không gắn anchor, weight phân bổ trên toàn đoạn. JSON cũ không có shots
vẫn dùng khoảng hình cũ, được ghi ở `legacy_single_range_segments`; không
tuyên bố kiểu cắt đó giống mẫu. Caption mặc định tắt chỉ tắt lớp narration mới,
không xóa phụ đề/logo đã có trong video nguồn.

## Lệnh

```bash
./run.sh brief /duong/dan/phim.mp4          # ngân sách thời lượng
./run.sh new <job> /duong/dan/phim.mp4      # tạo job
./run.sh run <job>                          # chạy tới cổng duyệt kế tiếp
./run.sh check <job>                        # kiểm tra review.json + ước tính thời lượng
```

Đây là mặc định trong `config/default.yaml`. Watermark đổi ở
`render.picture_style.watermark`; bỏ chuỗi chữ để tắt. Nguồn có viền đen được
ước lượng và crop trước khi fit để tránh viền kép; kiểm tra hình với nguồn tối.
Mặc định `fit_mode: cover` crop giữa để hình phủ hết chiều ngang vùng điện ảnh,
không tạo viền đen hai bên như cách fit ảnh 16:9 vào vùng rộng. Với nguồn dọc
hoặc chủ thể bị mất sau crop, chọn `fit_mode: contain` hoặc chuẩn bị shot/crop
phù hợp; contain giữ toàn hình và có thể thêm viền hai bên.
Không kéo dãn hình, không thêm meme sticker hoặc hiệu ứng chuyển cảnh không
quan sát được trong mẫu.
