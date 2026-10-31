# Antigravity READ — yêu cầu phân tích video local

## Phạm vi và quyền

Người dùng yêu cầu bạn phân tích video trong project này và trả file Markdown về ổ đĩa.
Đây là nhiệm vụ READ; chưa viết review.json, chưa dựng video, chưa sửa mã pipeline.
Chỉ đọc video/request và dùng tool local hiện có. Chỉ ghi artifact vào output_directory bên dưới.
Không sửa/xóa video nguồn, không ghi đè timeline phim khác, không cài package/model mới,
không tìm/lấy API key hoặc token, không gọi Gemini/OpenAI API từ script.
Không đổi cấu hình toàn cục hệ thống, cho phép tự động thực thi công cụ trong scope (auto-proceed, không cần submit quyền thủ công từng lệnh), không truy cập dữ liệu cá nhân ngoài scope.
Không tải phim khác từ Internet. Có thể dùng Antigravity với phiên đăng nhập hiện tại.
Nếu công cụ không đọc được đầy đủ hình/âm thanh hoặc có giới hạn file, báo rõ;
không thay phân tích video thật bằng trí nhớ về phim hay tên file.

## Job

- request_id: ga_kim_thoa_ep01-6876479dc365
- project: D:\workplace_make_firm\review_firm_china\ai-video-review
- source_video: D:\workplace_make_firm\review_firm_china\ai-video-review\input\videos\ga_kim_thoa_ep01.mp4
- source_size_bytes: 924668949
- source_duration_seconds: 2912.152517
- resolution: 1920x1080
- fps: 25.0
- output_directory: D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\ga_kim_thoa_ep01
- output_file: D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\ga_kim_thoa_ep01\timeline.md

Tên file chỉ là nhãn do người dùng đặt. Không xác nhận năm phát hành/phiên bản tác phẩm
chỉ từ tên “Moana (2026)” hoặc từ kiến thức ngoài video.

## Mục tiêu review sau bước READ

- Tổng review: 1164.861–1456.076 giây (40–50% nguồn).
- Mục tiêu 45%: 1310.469 giây.
- Đánh giá cuối: 10–20 giây, mục tiêu 15; đã tính trong tổng.
- Lời kể sau này hài hước, trẻ trung, hợp tác phẩm và cảm xúc; không bịa diễn biến.
- Preset sau này: normal, suspense, excited, serious, punchline, calm.
  Có thể gợi ý cảm xúc theo đoạn, nhưng đây không phải nhiệm vụ sinh TTS.
- Thời lượng cuối do TTS thật đo; không lặp hình/đệm im lặng để đủ tỷ lệ.

## Nội dung timeline.md bắt buộc

A. Thông tin nguồn và phạm vi thực sự đã phân tích.
Ghi rõ khoảng đã đọc hình, khoảng đã nghe/đọc thoại, khoảng chỉ xem ảnh mẫu và khoảng chưa đọc.
Không tuyên bố xem toàn bộ nếu mới lấy vài frame hoặc chỉ đọc metadata.

B. Tóm tắt trục truyện: mục tiêu, trở ngại, nguyên nhân → hành động → hậu quả,
bước ngoặt, quan hệ nhân vật, mở đầu/kết thúc trong chính file này.

C. Bảng nhân vật: tên, vai trò, nhận diện, mốc xuất hiện, căn cứ tên gọi,
mức chắc chắn. Nếu chưa rõ dùng NV01, NV02; không tự đặt tên.

D. Timeline chi tiết:
ID | source_start | source_end | nhân vật | hành động/tình tiết |
bằng chứng hình/thoại/chữ | mức chắc chắn.
Timestamp là giây tính từ đầu file, không reset; 0 <= start < end <= 2912.152517.
Chia theo diễn biến có ý nghĩa; không gộp nhiều phút thành một câu.
Bao phủ cả intro/credit/chuyển cảnh hoặc ghi rõ lý do bỏ qua.
Không làm giả độ chính xác từng frame; đánh dấu mốc ước lượng.

E. Đoạn hình gợi ý:
clip_id | timeline_id | source_start | source_end | visual_intent |
lý do chọn | âm thanh gốc nên giữ/tắt | mức chắc chắn.
Chuẩn bị đủ lựa chọn cho review gần nửa nguồn, không chỉ vài clip lặp lại.
Nêu vị trí phụ đề/logo gốc để tránh chồng subtitle Việt.
Flow dựng theo mẫu 1004: chuẩn bị chuỗi shot ngắn 1–2 giây thay vì một khoảng
hình dài cho cả đoạn kể; mỗi ý nên có hình hành động, vật thể hoặc phản ứng
khớp nội dung. Cung cấp range có dư footage cho TTS đo thật, ghi rõ ý nào được
minh họa; các timestamp vẫn phải từ nguồn thật. Kịch bản sau này gắn shot với
speech_unit_id để cắt theo ranh giới câu đọc. Không sao chép shot/timestamp
từ mẫu 1004 sang một phim khác. Khung đầu ra ngang 1920x1080 có viền đen,
watermark nhỏ; không thêm phụ đề narration lớn mặc định.

F. Chất liệu hài hước có căn cứ: timestamp + tình huống/tương phản + hướng câu đùa.
Tách câu đùa khỏi lời thoại thật; giữ nhịp ấm áp/nghiêm túc khi cần.

G. Đánh giá cuối 10–20 giây: điểm mạnh có căn cứ, hạn chế nếu quan sát được,
khán giả phù hợp, 1 gợi ý nhận xét ngắn và khoảng hình minh họa.
Không bịa nhận xét để đủ cấu trúc, không dùng lời kêu gọi xem tiếp thay đánh giá.

H. Bố cục review và ngân sách: hook → diễn biến → cao trào → kết truyện → đánh giá.
Cộng khoảng 1310.469 giây, đã gồm 15 giây nhận xét.

I. Hạn chế, mâu thuẫn, những khoảng chưa phân tích và việc cần làm tiếp.
Phân biệt quan sát trực tiếp, suy luận và thông tin chưa xác minh.
Không tự hợp thức hóa tình tiết mâu thuẫn.

## Contract xuất file

Tạo file UTF-8 Markdown THẬT tại output_file đã nêu, không chỉ trả bảng trong chat.
Không ghi vào data/timeline/timeline.md của phim cũ.
Nếu timeline.md đích đã tồn tại, dừng và hỏi trước khi ghi đè.

Bắt đầu file bằng YAML front matter:

```yaml
---
request_id: "ga_kim_thoa_ep01-6876479dc365"
analysis_status: complete
source_video: "D:\\workplace_make_firm\\review_firm_china\\ai-video-review\\input\\videos\\ga_kim_thoa_ep01.mp4"
source_duration_seconds: 2912.152517
---
```

analysis_status chỉ có:
- complete: thực sự phân tích đủ video, nêu cơ sở kiểm tra.
- partial: còn khoảng thiếu; liệt kê cụ thể khoảng nào, vì sao.
- blocked: không đọc được video/âm thanh hoặc thiếu khả năng/quyền; ghi lý do và bước cần user làm.

Không để trạng thái complete nếu chỉ dựa trên sample frame.
Nếu bị chặn, vẫn ghi timeline.md với status blocked nếu có quyền ghi, không bịa timeline.
Nếu ngay cả ghi file cũng bị chặn, trả rõ lỗi trong hội thoại.
Khi hoàn tất, trả đường dẫn file + status + phạm vi đã phân tích.
