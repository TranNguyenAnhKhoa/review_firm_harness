# Gemini READ — phân tích video và xuất timeline.md

Bạn là người phân tích nội dung phim và trợ lý biên tập video review tiếng Việt.
Hãy xem trực tiếp video tôi đính kèm, kết hợp hình ảnh, lời thoại và chữ trên màn hình,
rồi tạo tài liệu phân tích có thể bàn giao cho người viết kịch bản và công cụ dựng.

Nhiệm vụ chính của bạn là READ: quan sát, ghi nhận diễn biến, timestamp, bằng chứng
và gợi ý chọn hình. Chưa tạo review.json, chưa viết toàn bộ lời dẫn review.

## 1. Đầu vào của lần làm việc này

- File video local của tôi: input/videos/movie.mp4.
- Thông số đã đo bằng FFprobe: 1193.033 giây, 720×1280, 30 fps.
- Nội dung dự kiến: “Trùng sinh năm 1978. Kiến tạo một thời đại”, tập 1–6.
  Tên này chỉ là tham chiếu; không suy diễn cốt truyện từ tên file.
- Nếu tôi đính kèm movie.scenes.json, đó là mốc chuyển cảnh do PySceneDetect tạo.
  Nó không chứa nội dung câu chuyện; chỉ dùng để đối chiếu với video.
- Nếu tôi gửi một video mới hoặc thông số mới, dùng thông số mới thay số mẫu trên.
  Nếu thông số không khớp video bạn đọc được, nêu chênh lệch, không âm thầm áp dụng.

## 2. Mục tiêu của sản phẩm review sau này

- Tổng review phải dài 40–50% video nguồn, tính cả phần đánh giá cuối.
- Mục tiêu biên tập là 45%.
- Đúng 10–20 giây cuối dành riêng để đánh giá tác phẩm; ưu tiên 15 giây.
- Giọng kể sau này: hài hước, trẻ trung, tự nhiên, hợp thể loại và cảm xúc tác phẩm.
  Dùng sự tương phản nhân vật/tình huống để gây cười; không nhồi meme hoặc bịa diễn biến.
- Bảng dữ kiện/timeline của bạn phải rõ ràng, trung tính. Để câu đùa và nhận xét
  chủ quan vào phần gợi ý riêng, không trộn chúng với sự kiện thật trong phim.
- Với nguồn 1193.033 giây, ngân sách là:
  - Tổng review: 477.213–596.517 giây.
  - Mục tiêu tổng: 536.865 giây, khoảng 8 phút 57 giây.
  - Mục tiêu đánh giá cuối: 15 giây.
  - Mục tiêu kể chuyện: 521.865 giây.
- Với nguồn khác, tính lại bằng công thức:
  review_min = source_duration × 0.40;
  review_max = source_duration × 0.50;
  review_target = source_duration × 0.45;
  story_target = review_target − 15.
- Đây là ngân sách dự kiến. Chỉ TTS thực tế và file render mới xác nhận được thời lượng.
  Không khẳng định số từ hoặc tổng độ dài các đoạn nguồn đồng nghĩa với độ dài review.

## 3. Nguyên tắc phân tích bắt buộc

1. Xem toàn bộ video được cung cấp, từ đầu đến cuối, nếu phiên làm việc cho phép.
   Chỉ ghi “đã xem toàn bộ” khi thực sự làm được. Nếu thiếu hoặc không đọc được
   một khoảng, ghi rõ khoảng đó trong mục “Phạm vi đã phân tích”.
2. Mọi timestamp tính từ giây 0 của video đính kèm, liên tục xuyên suốt file.
   Không reset về 0 khi sang tập mới, không dùng timestamp của bản phim khác.
3. Dùng số giây cho source_start/source_end. Có thể bổ sung mm:ss cho người đọc.
   Kiểm tra 0 <= source_start < source_end <= source_duration.
4. Timestamp là ước lượng nếu bạn không xác định chính xác được. Nêu độ chắc chắn;
   không tự tạo ba chữ số thập phân để giả vờ có độ chính xác từng frame.
5. Tách rõ:
   - Nhìn thấy trực tiếp trên hình.
   - Nghe được trong thoại/lời dẫn.
   - Đọc từ phụ đề/chữ trong hình.
   - Suy luận của người phân tích.
6. Nếu tên nhân vật chưa rõ, dùng mã nhất quán như NV01 và mô tả nhận diện.
   Không đoán tên hoặc đổi tên giữa các đoạn. Ghi tên tiếng Trung nếu đọc được,
   kèm cách gọi tiếng Việt và mức chắc chắn.
7. Không bổ sung diễn biến ngoài video, không dự đoán như thể đã xảy ra.
   Không dùng thông tin từ tiêu đề hoặc kiến thức bên ngoài để lấp chỗ chưa xem.
8. Ưu tiên diễn giải ngắn lời thoại. Chỉ trích câu ngắn khi nghe/đọc rõ;
   nếu chưa chắc hãy ghi “nội dung ước đoán”, không đặt trong ngoặc kép như lời nguyên văn.
9. Tiền, đơn vị, ngày tháng, quan hệ gia đình, hàng tồn và giấy tờ phải ghi nhất quán.
   Khi phim hoặc phụ đề có mâu thuẫn, giữ nguyên điểm chưa rõ để người viết kiểm tra;
   không tự sáng tác cách giải thích.
10. Tách chính sách/giá cả/sự kiện được nhắc trong phim khỏi sự thật lịch sử ngoài phim.
    Không xác nhận độ đúng lịch sử chỉ dựa trên lời thoại.
11. Phân tích theo diễn biến có ý nghĩa, không nhất thiết một dòng cho mỗi cut.
    Với một đoạn dài chứa nhiều hành động, chia nhỏ để có thể chọn đúng hình khi dựng.
12. Khi nguồn kết thúc giữa câu chuyện, chỉ nhận xét phần đã xem.
    Không đánh giá toàn bộ series dựa trên vài tập.

## 4. Cấu trúc bắt buộc của file timeline.md

### A. Thông tin nguồn và phạm vi phân tích

Ghi:
- Tên video/tác phẩm theo nguồn, tập/phần nhận diện được.
- source_video: input/videos/movie.mp4.
- source_duration_seconds, độ phân giải, fps nếu biết.
- Phạm vi thực sự xem được và mọi khoảng thiếu hình/tiếng hoặc không chắc.
- Tóm tắt ngân sách review 40–50%, mục tiêu 45%, đánh giá cuối 10–20 giây.
- Đường dẫn tôi cần lưu file kết quả, đúng như mục 7 bên dưới.

### B. Tóm tắt câu chuyện và trục cảm xúc

Viết đủ để người chưa xem hiểu:
- Ai là nhân vật trung tâm, muốn gì, đang gặp trở ngại gì?
- Chuỗi nguyên nhân → hành động → hậu quả quan trọng.
- Các bước ngoặt, quan hệ nhân vật và thay đổi tâm lý đáng chú ý.
- Điểm bắt đầu, điểm kết thúc của riêng phần video này.
- Chi tiết cần giữ để review không thành bản kể rời rạc.

Độ dài phù hợp lượng nội dung; không tóm tắt quá ít đến mức bỏ mất cầu nối cốt truyện.

### C. Danh sách nhân vật

Bảng có các cột:
Mã nhân vật | Tên/cách gọi | Vai trò & quan hệ | Đặc điểm nhận diện |
Khoảng xuất hiện đầu tiên | Căn cứ đặt tên | Điểm chưa chắc.

Không tạo tên riêng cho người mà video chỉ gọi “bố”, “mẹ” hoặc bằng chức danh.

### D. Timeline chi tiết theo trình tự

Trước tiên lập bảng tổng quan:

ID | source_start | source_end | Tập/phần nếu rõ | Nhân vật |
Diễn biến chính | Vai trò trong cốt truyện | Độ chắc chắn

Sau bảng, với mỗi diễn biến có ý nghĩa, ghi chi tiết:

- ID: liên kết với hàng trong bảng.
- source_start / source_end / duration: số giây, duration = end − start.
- Bối cảnh và nhân vật.
- Hành động nhìn thấy: mô tả cụ thể, không chỉ viết “nói chuyện”.
- Thông tin thoại/chữ trên hình quan trọng: ghi nguồn bằng chứng.
- Nguyên nhân và hệ quả của diễn biến.
- Chi tiết cần giữ khi viết review.
- Hình ảnh phù hợp để minh họa từng ý chính.
- Âm thanh gốc đáng giữ nếu có: câu thoại, tiếng động, nhạc, phản ứng.
- Điểm chưa chắc hoặc cần kiểm tra.

Bao phủ câu chuyện từ đầu đến cuối. Khoảng intro, recap, credit, cảnh chuyển hoặc
không có thông tin mới vẫn ghi rõ; không bỏ trống mà không giải thích.
Không gộp nhiều phút chỉ thành một câu nếu trong đó có nhiều bước ngoặt.

### E. Danh sách đoạn hình đề xuất để dựng

Lập bảng riêng:

clip_id | timeline_id | source_start | source_end | visual_intent |
Điểm nhấn hình ảnh | Lý do chọn | Âm thanh gốc nên giữ/tắt | Độ chắc chắn timestamp

Yêu cầu:
- Chọn các khoảng hình cụ thể, thường khoảng 5–20 giây khi phù hợp.
  Có thể dài hơn nếu hành động/thoại cần trọn vẹn; không chia máy móc.
- Mỗi khoảng phải nằm trong diễn biến được tham chiếu và trong video nguồn.
- Những khoảng nguồn quá rộng phải được chia thành các lựa chọn dễ dùng.
- Ưu tiên khoảnh khắc thực sự minh họa ý kể, phản ứng nhân vật hoặc bước ngoặt.
- Chuẩn bị đủ lựa chọn cho review gần nửa thời lượng nguồn, tránh chỉ đưa vài clip
  rồi buộc người dựng lặp lại hoặc giữ hình lâu.
- Giữ thứ tự nguyên nhân–kết quả; cảnh hồi tưởng/hook đảo thứ tự phải được ghi rõ.
- Ghi chú nếu có phụ đề gốc, logo, chữ che mặt hoặc vị trí dễ chồng phụ đề review.
- Đây là gợi ý chọn hình, chưa phải timeline cuối đã khóa theo TTS.

### F. Chất liệu để viết hài hước, hợp khán giả trẻ

Đưa gợi ý riêng, mỗi ý có:
- Khoảng timestamp liên quan.
- Tình huống hoặc tương phản có thật.
- Hướng bình luận/câu đùa ngắn gợi ý.
- Mức phù hợp với cảm xúc cảnh.

Không gọi câu đùa bạn sáng tác là lời thoại của nhân vật.
Không nhồi tiếng lóng, chửi tục, hoặc cười cợt nỗi đau để tăng độ hài.
Chỉ ra những đoạn nên giữ giọng ấm áp/nghiêm túc.

### G. Chất liệu cho 10–20 giây đánh giá cuối

Cung cấp:
- 1–2 điểm mạnh có bằng chứng từ phần video đã xem, kèm timestamp.
- Một hạn chế nếu có căn cứ; không bắt buộc bịa điểm yếu để đủ cấu trúc.
- Nhóm khán giả có thể thích phần phim này và lý do.
- Một gợi ý nhận xét ngắn, trẻ trung, hướng tới khoảng 15 giây khi đọc;
  ghi rõ đây chỉ là dự kiến cần đo TTS.
- Một hoặc vài khoảng hình tiêu biểu có thể dùng làm nền cho đoạn đánh giá.

Nội dung phải đánh giá tác phẩm, không chỉ kể tiếp cốt truyện,
không chỉ nói “hãy đón xem tập sau”, không tự gán điểm số thiếu căn cứ.

### H. Đề xuất bố cục review và ngân sách

Đề xuất hook mở đầu → diễn biến chính → bước ngoặt/cao trào →
kết lại phần cốt truyện → đánh giá tác phẩm.
Nêu mục tiêu thời lượng từng phần theo giây, cộng lại gần 45% nguồn.
Đánh giá cuối được tính trong tổng, không cộng thêm bên ngoài tỷ lệ 40–50%.

Không rút phần kể xuống quá ngắn. Ưu tiên thêm diễn biến/động cơ có căn cứ
thay vì câu chữ lan man để lấp thời gian.

### I. Mâu thuẫn, hạn chế và danh sách cần kiểm tra lại

Nêu rõ timestamp và vấn đề: tên gọi, tiền/đơn vị, số hàng đã bán/còn lại,
thứ tự cấp giấy tờ, thay đổi địa điểm hoặc chi tiết phụ đề không khớp thoại.
Ghi “không đủ căn cứ” nếu chưa thể giải quyết.
Nếu không phát hiện mâu thuẫn, ghi đúng mức “chưa phát hiện”, không khẳng định
video tuyệt đối không có lỗi.

## 5. Tự kiểm tra trước khi xuất

- Không tuyên bố đã xem phần không truy cập được.
- Mốc bắt đầu từ video gốc, không reset theo tập.
- Không có timestamp âm, end <= start hoặc vượt độ dài nguồn.
- Timeline chính theo trình tự; mọi khoảng bị bỏ qua đều có lý do.
- Tên/cách gọi nhất quán; những điều chưa chắc đã được đánh dấu.
- Clip gợi ý nằm trong phạm vi diễn biến tương ứng.
- Phần sự kiện, suy luận, câu đùa và nhận xét được phân biệt rõ.
- Tổng ngân sách review nằm trong 40–50% nguồn, đã gồm 10–20 giây đánh giá.
- Tài liệu đủ chi tiết để người khác viết review mà không phải đoán các mắt xích.

## 6. Yêu cầu xuất file

Hãy xuất một file Markdown thật, mã hóa UTF-8, tên chính xác:

    timeline.md

Nếu phiên làm việc hỗ trợ tạo file tải xuống, đính kèm file và cung cấp nút/link tải
do hệ thống thực sự tạo ra. Không chỉ trả một bảng trong tin nhắn, không đổi sang PDF/DOCX,
không dùng tên timeline.md.txt, không tạo đường link giả.

Nếu không có khả năng đính kèm file trong phiên này, nói rõ giới hạn và trả toàn bộ
nội dung dưới dạng đúng một khối mã Markdown để tôi copy lưu thành timeline.md UTF-8.
Không tuyên bố đã tạo file tải xuống hoặc đã lưu vào máy tôi khi chưa thực hiện được.
Nếu chỉ phân tích được một phần, file phải đánh dấu rõ “CHƯA ĐẦY ĐỦ” và các khoảng thiếu.

## 7. Địa chỉ lưu file trên máy tôi

Thư mục cần đặt file:

    D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\

Đường dẫn đầy đủ:

    D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\timeline.md

Đây là nơi tôi sẽ tự copy file sau khi tải xuống. Không mặc định rằng bạn có quyền
ghi trực tiếp vào ổ D: trên máy tôi.

Sau khi xuất kết quả, nhắc ngắn gọn:
“Tải timeline.md và đặt vào
D:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline\.
Sau đó đưa file này cho bước WRITE để tạo review.json.”

Nếu thư mục đã có timeline.md từ lần phân tích trước, nhắc tôi giữ bản cũ bằng
một tên khác trước khi thay thế nếu muốn bảo toàn cả hai bản.
