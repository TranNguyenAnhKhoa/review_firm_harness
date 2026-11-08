# READ: phân tích phim cho job {{job}}

Bạn là người xem phim và ghi chép cho một kênh review phim tiếng Việt. Nhiệm vụ: xem phim thật
rồi ghi MỘT file Markdown UTF-8 tại:

    {{output_file}}

Đây chỉ là bước READ. Không viết review.json, không dựng video, không sửa code hay cấu hình.
Chỉ được ghi đúng file trên. Không xoá/sửa video hay file khác. Không tải gì từ Internet.
Không bịa: mọi tình tiết phải đến từ hình, tiếng hoặc chữ trên màn hình của chính file này,
không đến từ trí nhớ về tác phẩm hay từ tên file.

## Job

- request_id: {{request_id}}
- tên job / tiêu đề: {{job}} / {{title}}
- video nguồn: {{source_name}}
- thời lượng: {{duration}} giây ({{duration_hms}}), {{width}}x{{height}}, {{fps}} fps

## Tài liệu để xem (chỉ những file này)

{{materials}}

{{engine_instructions}}

## Các bước, làm đúng thứ tự, không thêm việc khác

1. Xem lần lượt TẤT CẢ tài liệu liệt kê ở trên, từ đầu đến hết phim.
2. Ghi `timeline.md` một lần, đủ các mục A-I bên dưới.
3. Đọc lại file vừa ghi, sửa chỗ thiếu/sai (front matter, cột bảng, số giây), rồi kết thúc.

Không mở file nào khác: không đọc mã nguồn, test, cấu hình hay tài liệu của harness, không đọc job khác.
Mọi quy tắc cần thiết đã có trong yêu cầu này.

## Ngân sách của bản review sau này (để bạn chuẩn bị đủ chất liệu)

- Tổng review {{total_min}}-{{total_max}} giây (40-50% nguồn), mục tiêu {{total_target}} giây,
  đã gồm 10-20 giây đánh giá cuối. Phần kể chuyện khoảng {{story_target}} giây.
- Giọng đọc khoảng 5,4 tiếng/giây, nên lời kể cần khoảng {{story_words}} tiếng: timeline phải đủ chi tiết
  để viết chừng ấy lời mà không lặp ý.
- Dựng theo mẫu 1004: shot ngắn 1-2 giây, cắt thẳng theo câu đọc, hình phải khớp đúng ý câu kể.

## Nội dung bắt buộc của timeline.md

Mở đầu bằng YAML front matter đúng như sau (giữ nguyên request_id và thời lượng):

```yaml
---
request_id: "{{request_id}}"
analysis_status: complete
source_duration_seconds: {{duration}}
---
```

`analysis_status`: `complete` khi đã xem hết phim; `partial` khi còn khoảng chưa xem (liệt kê ở mục I);
`blocked` khi không xem được video (ghi lý do, không viết timeline giả).

A. Nguồn và phạm vi: khoảng nào đã xem hình, khoảng nào nghe/đọc được thoại, khoảng nào bỏ qua và vì sao.

B. Trục truyện: mục tiêu, trở ngại, nguyên nhân, hành động, hậu quả, bước ngoặt, mở đầu và kết thúc
   của chính file này.

C. Bảng nhân vật: `| Mã | Tên | Nhận diện (trang phục, gương mặt) | Vai trò | Mốc xuất hiện | Căn cứ tên gọi | Chắc chắn |`.
   Chưa rõ tên thì dùng NV01, NV02; không tự đặt tên.

D. Timeline chi tiết, MỘT bảng Markdown với đúng các cột:
   `| ID | source_start | source_end | Nhân vật | Diễn biến | Bằng chứng (hình/thoại/chữ) | Chắc chắn |`
   - Thời gian là số giây tính từ đầu video nguồn (số thập phân, không dùng mm:ss), 0 <= start < end <= {{duration}}.
   - Mỗi dòng là một diễn biến có nghĩa, thường 20-90 giây; cần khoảng {{min_rows}} dòng trở lên cho phim này.
   - Phủ kín từ 0 đến hết phim, kể cả intro, credit, chuyển cảnh (ghi rõ là credit).
   - Thoại quan trọng thì trích nguyên văn ngắn trong cột bằng chứng.

E. Shot gợi ý, MỘT bảng Markdown với đúng các cột:
   `| clip_id | timeline_id | source_start | source_end | Nội dung hình | Dùng cho ý kể | Âm gốc |`
   - Mỗi shot dài 1-4 giây, nằm trọn trong một cảnh quay (không vắt qua điểm cắt cảnh).
   - Ưu tiên hành động, gương mặt phản ứng, vật thể quan trọng, khoảnh khắc thoại đáng giữ.
   - Cần ít nhất {{min_shots}} shot, rải khắp phim theo diễn biến. Không lặp lại cùng một khoảng.
   - Ghi vị trí phụ đề cứng/logo gốc nếu có.

F. Chất liệu hài hước có căn cứ: thời điểm, tình huống/tương phản, hướng câu đùa. Tách câu đùa khỏi thoại thật.
   Đoạn buồn hay nghiêm túc thì ghi rõ để người viết không pha trò sai chỗ.

G. Gợi ý đánh giá cuối (10-20 giây khi đọc): một điểm mạnh có căn cứ, một hạn chế nếu thấy được,
   khán giả hợp, và 2-3 shot nền.

H. Bố cục review gợi ý: hook ngay câu đầu, diễn biến, cao trào, kết, đánh giá; ước lượng giây cho từng phần,
   cộng lại khoảng {{total_target}} giây.

I. Hạn chế: khoảng chưa xem, chỗ không chắc, mâu thuẫn. Phân biệt quan sát trực tiếp với suy luận.
{{reviewer_note}}
Khi xong, trả lời ngắn: đường dẫn file, analysis_status, phạm vi đã xem.
