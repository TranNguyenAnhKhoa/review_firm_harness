# Quy tắc biên tập review

## Thời lượng bắt buộc

- Tổng video review, bao gồm đoạn đánh giá cuối: 40–50% video nguồn.
- Mục tiêu khi viết: 45% nguồn, chừa khoảng an toàn cho nhịp TTS và làm tròn frame.
- Đúng một segment cuối có `section: "assessment"`, dài 10–20 giây; ưu tiên 15 giây.
- Các segment trước đó có `section: "story"`.
- Phần kể chuyện mục tiêu = 45% thời lượng nguồn trừ 15 giây.
- Thời lượng quyết định bằng TTS đã decode sang PCM và video xuất cuối.
  `target_duration` hay số từ chỉ là dự kiến, không thay được đo audio.
- Nếu thiếu thời lượng: viết thêm diễn biến, động cơ, quan hệ nhân vật và bình luận có căn cứ.
  Nếu dư: bỏ lặp ý và rút câu. Không kéo chậm giọng, đệm im lặng, lặp clip hoặc giữ hình
  vô nghĩa chỉ để đủ tỷ lệ. Freeze-frame hiện có chỉ phục vụ narration dài hơn một cảnh ngắn.

Với movie.mp4 dài 1193.033 giây:
tổng 477.213–596.517 giây, mục tiêu 536.865 giây; story khoảng 521.865 giây,
assessment khoảng 15 giây. Bản review cũ 287 giây chưa đạt chính sách này.

## Giọng điệu

Mặc định theo mẫu 1004: mở ngay bằng hành động/tình huống gây tò mò,
không chào kênh hoặc giới thiệu dài. Kể liên tục theo nguyên nhân → hành động
→ phản ứng/hậu quả; đưa lời thoại có căn cứ vào lời kể bằng “liền hỏi”, “bảo”,
“nghe vậy”. Xen bình luận ngắn từ tình huống, không biến mọi câu thành punchline.
Thường một đoạn 8–15 giây, câu ngắn/vừa, nhịp kể mục tiêu khoảng 5,4 tiếng/giây.
Giữ Bảo Trang; không ghi pitch khác 0. Shot ưu tiên 1–2 giây, hình khớp hành động
và gương mặt phản ứng; có thể lâu hơn ở điểm cần cảm xúc.
Chi tiết schema/anchor và giới hạn đo: docs/reference1004-flow.md.

Hài hước, trẻ trung, nói chuyện tự nhiên. Dùng câu ngắn, chuyển ý rõ, có nhịp kể.
Câu đùa phải xuất phát từ tính cách, tương phản hoặc tình huống của tác phẩm.
Không cần chèn một câu đùa vào mọi câu; xen nhịp nghiêm túc ở chỗ cần cảm xúc.
Tránh nhồi tiếng lóng, meme nhanh lỗi thời, chửi tục hoặc đùa lạc bối cảnh.
Không dùng lời chế làm lời thoại thật; không bịa tình tiết để tạo punchline.

Với phim trùng sinh năm 1978:
- Khai thác tương phản người con tính toán tự tin và ông bố hay lo.
- Ví dụ giọng kể: “Bố đã chuẩn bị đường rút lui, còn con đang chuẩn bị chốt đơn.”
- Ví dụ: “Vốn thì mỏng, nhưng bản kế hoạch trong đầu anh lại hơi dày.”
- Giữ sự ấm áp ở các đoạn bố mẹ, gia đình và cơ hội sống lại.
- Không chế nhạo cảnh hấp hối hoặc biến nỗi khổ của gia đình thành trò cười.

## Đánh giá tác phẩm ở cuối

Đây là nhận xét, không phải kể nốt cốt truyện hay chỉ kêu gọi xem phần tiếp.
Trong 10–20 giây, nêu một điểm mạnh có căn cứ, một hạn chế nếu có căn cứ,
và tác phẩm hợp người xem nào. Phân biệt cảm nhận cá nhân với tình tiết.
Không tự gán điểm số hoặc nhận định về diễn xuất/hình ảnh khi chưa có căn cứ.

Ví dụ định hướng cho phần phim đã được cung cấp:
“Điểm cuốn của phần này là cặp bố con: một người tính đường tiến,
một người lo đường lui. Mô-típ biết trước tương lai khá quen,
nhưng ai thích trùng sinh làm ăn và tình thân sẽ dễ xem tiếp.”

Ví dụ chỉ minh họa giọng văn; phải đo TTS để biết có đạt 10–20 giây hay không.

## Speech unit và khoảng nghỉ

Narration hỗ trợ string hoặc mảng speech unit có text/emotion.
Preset và pause dành cho nhịp kể tự nhiên, không phải công cụ kéo đủ quota.
Tổng review tính cả pause hợp lý; assessment kiểm tra riêng duration audio TTS
không gồm silence chèn và duration timeline cuối. Đổi tốc độ phải đo lại.
Không suy ra chất lượng diễn xuất chỉ từ nhãn emotion; cần nghe duyệt.
Chi tiết schema/override: docs/voice-and-emotion.md.
