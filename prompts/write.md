# WRITE: viết kịch bản review cho job {{job}}

Bạn là người viết kịch bản review phim tiếng Việt. Đọc timeline đã được duyệt rồi ghi MỘT file JSON tại:

    {{output_file}}

Chỉ ghi đúng file đó (UTF-8, JSON hợp lệ, không kèm chữ nào ngoài JSON). Không sửa timeline, code hay cấu hình.

## Đầu vào

- Timeline đã duyệt (nguồn sự thật duy nhất về diễn biến và thời gian): {{timeline}}
- Quy tắc biên tập: {{guidelines}}
- Mẫu JSON có speech unit và shot: {{example}}
- Danh sách điểm cắt cảnh (giây): {{scenes}}
- Phim: "{{title}}", dài {{duration}} giây.

Chỉ đọc các file trên. Không đọc mã nguồn, test hay cấu hình của harness, không đọc job khác.

## Ngân sách (đo bằng giọng đọc thật sau bước này)

- Tổng review {{total_min}}-{{total_max}} giây, mục tiêu {{total_target}} giây, GỒM đoạn đánh giá cuối.
- Đúng MỘT segment cuối `"section": "assessment"`, đọc mất 10-20 giây (nhắm 15 giây, khoảng 80 tiếng).
- Phần kể chuyện nhắm {{story_target}} giây. Giọng Bảo Trang đọc khoảng 5,4 tiếng/giây,
  nên toàn bộ lời kể cần khoảng {{story_words}} tiếng (đếm theo từ cách nhau bởi dấu cách).
- Không dùng khoảng lặng, đọc chậm hay lặp hình để đủ thời lượng. Thiếu thì viết thêm diễn biến có căn cứ.

## Giọng văn

- Vào thẳng tình huống ở câu đầu, không chào kênh, không giới thiệu dài.
- Kể nối tiếp nguyên nhân, hành động, phản ứng, hậu quả; đưa thoại có căn cứ vào lời kể ("liền hỏi", "nghe vậy").
- Hài hước, trẻ trung từ tình huống và tương phản nhân vật; không nhồi meme, không bịa tình tiết hay lời thoại.
  Đoạn buồn giữ nhịp nghiêm túc.
- Đánh giá cuối là nhận xét: điểm mạnh có căn cứ, hạn chế nếu có, khán giả hợp. Không kể tiếp, không "đón xem tập sau".

## Định dạng JSON

```json
{
  "title": "Tên bản review",
  "segments": [
    {
      "id": 1,
      "section": "story",
      "source_start": 120.0,
      "source_end": 168.0,
      "visual_intent": "Hình gì minh hoạ đoạn này",
      "keep_original_audio": true,
      "narration": [
        {"id": "s1u1", "text": "Câu kể thứ nhất.", "emotion": "normal"},
        {"id": "s1u2", "text": "Câu kể thứ hai.", "emotion": "suspense"}
      ],
      "shots": [
        {"source_start": 121.0, "source_end": 123.5, "speech_unit_id": "s1u1", "weight": 1},
        {"source_start": 130.0, "source_end": 132.0, "speech_unit_id": "s1u1", "weight": 1},
        {"source_start": 140.0, "source_end": 143.0, "speech_unit_id": "s1u2", "weight": 1}
      ]
    }
  ]
}
```

Quy tắc kiểm tra tự động (sai là bị trả lại):

1. `id` segment là số nguyên dương, không trùng. Segment kể dùng `"section": "story"`; segment cuối cùng duy nhất là `"assessment"`.
2. `0 <= source_start < source_end <= {{duration}}`. Mỗi shot nằm trong `source_start`-`source_end` của segment.
3. `narration` là mảng speech unit `{id, text, emotion}`; `id` unit không trùng trong segment;
   emotion là một trong normal, suspense, excited, serious, punchline, calm. Một unit thường 8-25 tiếng.
4. Shot có `speech_unit_id` thì MỌI shot của segment phải có, theo đúng thứ tự unit, unit nào cũng có ít nhất một shot.
   Tối đa 24 shot mỗi segment. Mỗi shot 1-4 giây footage, lấy từ bảng shot (mục E) hoặc timeline đã duyệt,
   nằm trọn trong một cảnh (không vắt qua điểm cắt cảnh).
5. Footage của segment phải dài hơn lời đọc của nó: tổng độ dài các shot nên gấp 1,2 lần trở lên thời gian đọc
   (số tiếng / 5,4).
6. Không thêm trường ngoài mẫu. Không dùng `pitch_hz` khác 0.

Segment kể thường 8-15 giây lời đọc với 5-10 shot. Thứ tự segment theo thứ tự kể, thường theo thời gian phim.
{{self_check}}{{reviewer_note}}{{revision}}
Khi xong, trả lời ngắn: đường dẫn file, số segment, ước lượng tổng số tiếng.
