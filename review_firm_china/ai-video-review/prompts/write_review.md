# Prompt WRITE — tạo review.json từ timeline

Đính kèm timeline, mẫu JSON của project và ngân sách thời lượng từ lệnh:

- File timeline đã tải từ Gemini:
  `D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\timeline.md`.
- Nếu chưa có file, dùng prompt `prompts/gemini_read.md` trước.
- Ngân sách thời lượng:

    python scripts/review_brief.py --video input/videos/movie.mp4

## Nội dung prompt để dùng

Bạn là người viết kịch bản review phim tiếng Việt. Dựa trên timeline tôi cung cấp,
hãy viết một kịch bản kể chuyện hài hước, trẻ trung và phù hợp với thể loại,
nhân vật, cảm xúc của tác phẩm. Thực hiện các quy tắc sau:

1. Tổng video review phải bằng 40–50% video nguồn, TÍNH CẢ phần đánh giá cuối.
   Nhắm mức 45% để có khoảng điều chỉnh sau khi đo TTS.
2. Dành đúng một segment cuối để đánh giá tác phẩm, nhắm 15 giây và bắt buộc
   nằm trong 10–20 giây khi đọc thực tế.
3. Ngân sách kể chuyện = mục tiêu tổng trừ mục tiêu đánh giá.
   Đừng rút hết nội dung thành bản tóm tắt quá ngắn. Giữ quan hệ nhân quả,
   động cơ, bước ngoặt, những đoạn đối thoại hoặc hành động đáng nhớ.
4. Hài hước từ tình huống và tương phản nhân vật; câu văn tự nhiên, dễ nghe,
   có điểm nhấn cho khán giả trẻ. Không nhồi meme, không bịa diễn biến/lời thoại.
   Tôn trọng nhịp cảm xúc của tác phẩm; đoạn buồn không bắt buộc phải pha trò.
5. Đoạn assessment phải đưa ra nhận xét về tác phẩm (điểm mạnh, hạn chế có căn cứ,
   đối tượng khán giả phù hợp), không phải chỉ tóm tắt hoặc câu “đón xem phần sau”.
6. Timestamp lấy từ video nguồn, source_start < source_end, không vượt thời lượng.
   Có thể dùng lại một đoạn hình phù hợp làm nền cho phần đánh giá cuối.
7. Chỉ trả một JSON theo schema dưới đây. ID duy nhất; không thêm trường ngoài schema.
   Các đoạn kể dùng section="story"; segment cuối dùng section="assessment".
8. target_duration nếu có chỉ là dự kiến biên tập. Không tuyên bố đạt tỷ lệ
   dựa trên số từ. Sau khi TTS đo duration, tôi sẽ gửi lại báo cáo để bạn chỉnh
   riêng phần quá ngắn hoặc quá dài. Không dùng im lặng để kéo dài.
9. Theo flow mẫu 1004: câu đầu vào thẳng tình huống/hành động gây tò mò, không
   intro chào kênh. Kể hành động và phản ứng theo nguyên nhân → hậu quả; dẫn
   thoại có căn cứ vào lời kể. Bình luận dí dỏm ngắn, không nhồi meme/punchline.
10. Mỗi đoạn mới phải có shots lấy từ timeline READ. Nhắm shot 1–2 giây và
    đoạn kể 8–15 giây, chọn nhân vật/hành động/phản ứng đúng với từng ý.
    Mỗi shot có source_start, source_end và weight dương; khoảng phải nằm trong
    source_start/source_end của segment. Không bịa timestamp, không dùng detector
    để tự suy ra nội dung. Thiếu dữ liệu thì yêu cầu bổ sung READ.
11. Ưu tiên narration dạng speech unit có id, shots có speech_unit_id tương ứng.
    Khi dùng anchor, phủ mọi unit theo thứ tự bằng ít nhất một shot; tối đa
    24 shot/segment. Ranh giới dựng theo thời lượng TTS đo thật, không theo
    target_duration dự đoán. Bảo Trang đọc khoảng 5,4 tiếng/giây; pitch_hz phải 0.
    Mẫu anchor: docs/reference1004-flow.md. Khung mặc định không có subtitle lời
    đọc lớn, không chèn meme/hiệu ứng lạ vào kịch bản.

Mẫu cấu trúc (timestamp, lời kể phải thay theo timeline thực tế):

    {
      "title": "Tên bản review",
      "source_video": "input/videos/movie.mp4",
      "segments": [
        {
          "id": 1,
          "section": "story",
          "narration": "Lời kể có diễn biến và bình luận dí dỏm...",
          "source_start": 0,
          "source_end": 30,
          "visual_intent": "Hình ảnh khớp với lời kể",
          "shots": [
            {"source_start": 0, "source_end": 5, "weight": 1},
            {"source_start": 5, "source_end": 10, "weight": 1},
            {"source_start": 10, "source_end": 15, "weight": 1},
            {"source_start": 15, "source_end": 20, "weight": 1},
            {"source_start": 20, "source_end": 25, "weight": 1},
            {"source_start": 25, "source_end": 30, "weight": 1}
          ],
          "keep_original_audio": true
        },
        {
          "id": 2,
          "section": "assessment",
          "narration": "Nhận xét điểm hay, hạn chế và khán giả phù hợp...",
          "source_start": 30,
          "source_end": 50,
          "visual_intent": "Hình ảnh tiêu biểu làm nền cho đánh giá",
          "shots": [
            {"source_start": 30, "source_end": 35, "weight": 1},
            {"source_start": 35, "source_end": 40, "weight": 1},
            {"source_start": 40, "source_end": 45, "weight": 1},
            {"source_start": 45, "source_end": 50, "weight": 1}
          ],
          "keep_original_audio": true
        }
      ]
    }

Đọc thêm docs/editorial-guidelines.md để giữ giọng văn nhất quán.

## Narration có nhịp và cảm xúc

Ưu tiên narration là mảng speech unit khi cần điều khiển nhịp. String cũ vẫn chạy.
Mỗi unit có text và emotion thuộc normal, suspense, excited, serious, punchline, calm.
Một unit thường 8–25 token; câu chốt ngắn là ngoại lệ. Không nhồi cảm xúc mọi câu.
Normal để kể; suspense bí ẩn; excited hành động; serious nhận xét;
punchline câu chốt; calm nhịp mềm. Chọn theo ý câu, không chỉ nhìn một từ khóa.
Có thể override rate_percent, pitch_hz, volume_percent, pause_before_ms, pause_after_ms
bằng số; bình thường chỉ cần text/emotion để config resolve preset.
Ví dụ thay trường narration của một segment:

    "narration": [
      {"text": "Anh ta bước vào căn phòng.", "emotion": "normal"},
      {"text": "Nhưng mọi thứ đã biến mất.", "emotion": "suspense"},
      {"text": "Cánh cửa phía sau bất ngờ bật tung!", "emotion": "excited"}
    ]

Ví dụ này chỉ minh họa format; nội dung thật phải bám timeline đã cung cấp.
Không tạo thêm narration_text hoặc trường lạ. Phần đánh giá cuối thường dùng serious,
nhưng section vẫn phải là assessment. Không dùng pause dài để đủ quota thời lượng.
Tham khảo docs/voice-and-emotion.md; phải đo TTS thật sau khi đổi preset/lời kể.
