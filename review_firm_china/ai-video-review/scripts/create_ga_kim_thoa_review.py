"""Build review.ga_kim_thoa_ep01.json with full editorial narration, speech units, and timestamps."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.pipeline.schema import ReviewScript, ReviewSegment, ReviewShot
from src.audio.speech import SpeechUnit

STORY_DATA = [
    # 1 - 5: Bối cảnh mở màn & chiếc trâm vàng
    (
        0.0, 50.0, "normal",
        "Vừa mở màn, Gả Kim Thoa đã ném khán giả vào ngay không khí xa hoa nhưng đầy toan tính của Thừa An Bá phủ.",
        "Tại đây, nhị tiểu thư Quân Đại đang ngồi trước gương đồng, tay mân mê chiếc trâm vàng nạm ngọc với vẻ mặt vô cùng đắc ý.",
        "Cứ ngỡ nàng ta sắp được gả vào hào môn danh giá nhất kinh thành để hưởng vinh hoa phú quý trọn đời.",
        [(2.0, 15.0), (20.0, 35.0), (38.0, 48.0)]
    ),
    (
        50.0, 100.0, "punchline",
        "Nhưng đời đúng là không như là mơ, tin tức từ tiền sảnh truyền vào khiến nụ cười trên môi tiểu thư tắt ngúm trong một nốt nhạc.",
        "Hôn ước từ nhỏ của nàng đúng là danh giá thật, đối tượng chính là Lục Trạc, thế tử phủ Anh Quốc Công lừng lẫy.",
        "Ngặt nỗi chàng thế tử vừa đánh trận trở về thì trúng tên độc, hiện đang nằm bất tỉnh nhân sự, hơi thở thoi thóp như ngọn đèn trước gió.",
        [(55.0, 68.0), (72.0, 85.0), (88.0, 98.0)]
    ),
    (
        100.0, 150.0, "suspense",
        "Phủ Anh Quốc Công thấy con trai sắp đi gặp diêm vương liền nảy ra sáng kiến tổ chức đám cưới gấp để xung hỷ trừ tà.",
        "Nói trắng ra là muốn rước Quân Đại về để nếu thế tử có mệnh hệ nào thì nàng sẽ trở thành góa phụ giữ trinh tiết cả đời.",
        "Tiểu thư kiêu kỳ nghe xong thì giãy nảy như đỉa phải vôi, một mực từ chối bước chân vào nấm mồ hôn nhân định mệnh này.",
        [(105.0, 120.0), (125.0, 138.0), (140.0, 148.0)]
    ),
    (
        150.0, 200.0, "excited",
        "Nàng gào thét trong phòng, đập phá đồ đạc và tuyên bố thẳng thừng rằng thà làm ni cô chứ quyết không lấy một khúc gỗ mục.",
        "Thế nhưng hôn ước là do Lão tổ tông và triều đình định đoạt, đâu phải thứ muốn quỵt là quỵt được dễ dàng như ăn kẹo.",
        "Trong lúc tranh cãi nảy lửa với tỳ nữ thân cận, chiếc trâm cài tóc đắt giá bất ngờ rơi xuống sàn gạch lạnh lẽo.",
        [(155.0, 170.0), (175.0, 185.0), (188.0, 198.0)]
    ),
    (
        200.0, 250.0, "serious",
        "Đầu trâm sắc nhọn vấy lên một vệt máu đỏ tươi, báo hiệu chuỗi sóng gió quyền mưu kinh thiên động địa sắp sửa ập đến.",
        "Bị dồn vào chân tường, Quân Đại bắt đầu vận dụng hết công suất chất xám trong đầu để tìm đường thoát thân cho bằng được.",
        "Và rồi, một kế hoạch tráo mận đổi đào điên rồ nhất chốn kinh kỳ đã được nàng ta âm thầm vạch ra trong bóng tối.",
        [(205.0, 218.0), (222.0, 235.0), (238.0, 248.0)]
    ),

    # 6 - 10: Tìm kiếm A Sửu & ngã giá
    (
        250.0, 300.0, "normal",
        "Rời khỏi khu phủ đệ nguy nga, ống kính máy quay lập tức chuyển cảnh sang một góc ngõ hẻm nghèo nàn và lầy lội ở ngoại thành.",
        "Tại đây, một cô gái trẻ trong bộ đồ vải thô rách rưới đang còng lưng gánh từng thùng dạ hương nặng trĩu đi đổ thuê kiếm sống.",
        "Dù mặt mũi lấm lem bùn đất và phải làm công việc bần hàn nhất thiên hạ, nhưng đôi mắt của cô gái vẫn sáng ngời và tràn đầy nghị lực.",
        [(255.0, 270.0), (275.0, 288.0), (290.0, 298.0)]
    ),
    (
        300.0, 350.0, "punchline",
        "Cô nàng này tên gọi là A Sửu, cái tên xấu xí người ta đặt cho để dễ nuôi, nhưng thực chất dung mạo ẩn sau lớp nhọ nồi lại là một tuyệt sắc giai nhân.",
        "Điều kỳ lạ hơn nữa là nếu rửa sạch mặt, A Sửu sở hữu ngũ quan giống nhị tiểu thư Quân Đại như hai giọt nước đúc ra từ một khuôn.",
        "Khán giả xem phim đến đây là ngửi thấy mùi thân thế tráo con từ thuở lọt lòng quen thuộc của phim gia đấu rồi.",
        [(305.0, 318.0), (322.0, 335.0), (338.0, 348.0)]
    ),
    (
        350.0, 400.0, "suspense",
        "A Sửu cày ngày cày đêm không phải vì đam mê lao động công ích, mà vì người mẹ nuôi đang mắc bạo bệnh nằm liệt giường trong túp lều rách nát.",
        "Tiền thuốc men mỗi ngày như muối bỏ bể, chủ tiệm thuốc liên tục đòi nợ khiến hai mẹ con rơi vào bước đường cùng không lối thoát.",
        "Đúng lúc tuyệt vọng nhất thì một cỗ xe ngựa sang trọng bất ngờ dừng lại ngay trước đầu con hẻm ổ chuột hôi hám.",
        [(355.0, 368.0), (372.0, 385.0), (388.0, 398.0)]
    ),
    (
        400.0, 450.0, "excited",
        "Quân Đại bước xuống xe, che mũi nhìn quanh với vẻ khinh bỉ tột cùng, nhưng khi nhìn thẳng vào mặt A Sửu thì ả ta chết trân tại chỗ.",
        "Sự giống nhau đến rợn người giữa hai số phận đối nghịch đã chứng minh cho ả thấy rằng chiếc phao cứu sinh của đời mình đã xuất hiện.",
        "Quân Đại lập tức cho người đuổi hết dân tình xung quanh rồi kéo A Sửu vào căn nhà tranh dột nát để bàn chuyện làm ăn lớn.",
        [(405.0, 418.0), (422.0, 435.0), (438.0, 448.0)]
    ),
    (
        450.0, 500.0, "serious",
        "Không vòng vo tam quốc, nàng thiên kim ném ngay một bọc bạc trắng lấp lánh lên chiếc bàn gỗ ọp ẹp trước sự ngỡ ngàng của cô gái nghèo.",
        "Bảo rằng chỉ cần A Sửu chịu đóng giả làm nhị tiểu thư bước lên kiệu hoa gả sang phủ Anh Quốc Công xung hỷ, tiền thuốc thang cho mẹ sẽ được lo trọn đời.",
        "Ngược lại, nếu dám từ chối hoặc để lộ nửa lời, cả hai mẹ con sẽ không còn đất dung thân ở cái kinh thành đầy cạm bẫy này.",
        [(455.0, 468.0), (472.0, 485.0), (488.0, 498.0)]
    ),

    # 11 - 15: Thỏa thuận & Bước vào phủ Thừa An Bá
    (
        500.0, 550.0, "normal",
        "A Sửu cầm thỏi bạc trên tay mà lòng nặng trĩu như đeo đá, nàng thừa hiểu bước chân vào chốn hào môn xung hỷ chẳng khác nào nhảy vào miệng cọp.",
        "Nhưng nhìn mẹ nuôi đang ho sặc sụa từng cơn trên manh chiếu rách, nàng biết mình không còn bất kỳ sự lựa chọn nào khác ngoài việc đánh cược mạng sống.",
        "Nàng ngẩng cao đầu đồng ý nhận lời giao dịch, mở ra bước ngoặt đổi đời đầy chông gai và hiểm họa khôn lường.",
        [(505.0, 518.0), (522.0, 535.0), (538.0, 548.0)]
    ),
    (
        550.0, 600.0, "suspense",
        "Màn đêm buông xuống, một cỗ xe ngựa bí mật đưa A Sửu luồn qua cửa sau để tiến vào nội viện Thừa An Bá phủ.",
        "Vừa cởi bỏ bộ đồ thô kệch và tắm rửa sạch sẽ, dung nhan thực sự của nàng lộ ra khiến ngay cả tỳ nữ thân cận của Quân Đại cũng phải giật mình thảng thốt.",
        "Quân Đại đứng cạnh nhìn bản sao của mình mà vừa mừng vừa sợ, trong lòng dấy lên nỗi ghen ghét khó tả trước nét đẹp thanh thuần của đối phương.",
        [(555.0, 568.0), (572.0, 585.0), (588.0, 598.0)]
    ),
    (
        600.0, 650.0, "punchline",
        "Khóa huấn luyện cấp tốc mang tên biến quạ thành công chính thức được kích hoạt ngay trong đêm tối tĩnh mịch.",
        "Một cô gái quen gánh phân bước đi thoăn thoắt giờ đây bị bắt học cách đi đứng nhẹ nhàng như hoa sen lướt trên mặt nước.",
        "Đầu đội bát nước đầy, lưng buộc thanh nẹp gỗ, hễ làm sánh ra một giọt là tỳ nữ lập tức dùng thước kẻ gõ vào tay cảnh cáo không thương tiếc.",
        [(605.0, 618.0), (622.0, 635.0), (638.0, 648.0)]
    ),
    (
        650.0, 700.0, "normal",
        "Thế nhưng điều khiến Quân Đại bất ngờ nhất là A Sửu học cực kỳ nhanh, ngón tay búp măng cầm quạt che mặt duyên dáng đến lạ kỳ.",
        "Từng dáng đi, nụ cười hé môi cho đến cái liếc mắt đưa tình của quý tộc đều được nàng tiếp thu và bắt chước chuẩn xác đến từng milimét.",
        "Dường như khí chất cao quý vốn đã nằm sẵn trong máu của nàng từ kiếp nào, chỉ chờ dịp này là bùng phát mạnh mẽ.",
        [(655.0, 668.0), (672.0, 685.0), (688.0, 698.0)]
    ),
    (
        700.0, 750.0, "serious",
        "Bên cạnh việc luyện hình thể, Quân Đại còn bắt A Sửu học thuộc lòng gia phả, tính cách và các mối quan hệ phức tạp trong gia đình quyền quý.",
        "Từ sở thích uống trà của Lão tổ tông cho đến tật xấu hay soi mói của các vị phu nhân đều phải ghi nhớ vanh vách không được phép sai một chữ.",
        "Bởi vì trong chốn hậu viện thâm sâu, chỉ cần sơ sẩy lộ ra một thói quen bần hàn là đầu sẽ rơi xuống đất ngay tức khắc.",
        [(705.0, 718.0), (722.0, 735.0), (738.0, 748.0)]
    ),

    # 16 - 20: Tình huống sơ hở & sự nhạy bén
    (
        750.0, 800.0, "suspense",
        "Trong lúc tập luyện dâng trà, tỳ nữ vô tình phát hiện trên cánh tay A Sửu có một vết sẹo dài do thời thơ ấu lao động vất vả để lại.",
        "Quân Đại hoảng hốt nhận ra tay tiểu thư lá ngọc cành vàng mịn màng không tì vết, nếu đêm tân hôn bị nhà trai thấy vết sẹo này thì lộ tẩy chắc chắn.",
        "Ả ta lập tức sai người mang bột phấn ngọc trai và cao mờ sẹo hảo hạng đến bôi trát nhiều lớp nhằm ngụy trang hoàn hảo vết tích.",
        [(755.0, 768.0), (772.0, 785.0), (788.0, 798.0)]
    ),
    (
        800.0, 850.0, "excited",
        "A Sửu cắn răng chịu đựng cảm giác xót rát khi lớp thuốc bôi lên da thịt mà không hề kêu ca lấy một tiếng nào.",
        "Sự bình tĩnh và ánh mắt kiên định của cô gái nghèo khiến đám gia nhân phục vụ bên cạnh bắt đầu có cái nhìn nể phục từ tận đáy lòng.",
        "Nàng hiểu rằng đây không chỉ là màn kịch gả thay, mà còn là cơ hội duy nhất để nàng thoát khỏi kiếp bùn đen tăm tối.",
        [(805.0, 818.0), (822.0, 835.0), (838.0, 848.0)]
    ),
    (
        850.0, 900.0, "normal",
        "Sáng hôm sau, tiếng chuông báo hiệu giờ thỉnh an vang lên khắp các dãy hành lang rợp bóng cây cổ thụ của Thừa An Bá phủ.",
        "Đây chính là bài thi sát hạch quan trọng đầu tiên: A Sửu phải diện kiến Lão tổ tông và mẫu thân trước khi chính thức bước lên kiệu hoa.",
        "Quân Đại đứng nấp sau tấm bình phong hoa điểu, mồ hôi ướt đẫm trán vì lo sợ kế hoạch tráo người bị bại lộ giữa ban ngày ban mặt.",
        [(855.0, 868.0), (872.0, 885.0), (888.0, 898.0)]
    ),
    (
        900.0, 950.0, "punchline",
        "A Sửu khoác lên mình bộ gấm hoa lộng lẫy, đầu cài trâm ngọc buông rủ, từng bước chân uyển chuyển tiến vào đại sảnh như một nàng tiên giáng trần.",
        "Điệu bộ đoan trang lễ phép, lời nói dạ vâng nhỏ nhẹ khiến các ma ma khó tính nhất trong phủ cũng phải gật gù khen ngợi tấm tắc.",
        "Quân Đại nấp bên trong nhìn ra mà tức anh ách, tự hỏi không biết đứa con gái đổ dạ hương này có uống nhầm thần dược quý tộc hay không.",
        [(905.0, 918.0), (922.0, 935.0), (938.0, 948.0)]
    ),
    (
        950.0, 1000.0, "suspense",
        "Lão phu nhân ngồi trên ghế bọc nhung khẽ nhấp ngụm trà sen, đôi mắt tinh đời nheo lại quan sát từng cử chỉ của đứa cháu gái yêu quý.",
        "Bà cụ đột nhiên gọi A Sửu lại gần rồi nắm lấy bàn tay nàng, nhẹ nhàng hỏi han về cảm xúc trước ngày đại hôn xuất giá.",
        "Không khí trong sảnh bỗng chốc đông cứng lại, ai nấy đều nín thở chờ đợi xem liệu có điều gì bất thường bị phát hiện hay không.",
        [(955.0, 968.0), (972.0, 985.0), (988.0, 998.0)]
    ),

    # 21 - 25: Màn đối đáp trước Lão phu nhân
    (
        1000.0, 1050.0, "excited",
        "Bằng sự thông minh trời phú, A Sửu khéo léo đáp rằng được gả cho thế tử Anh Quốc Công là phúc phận lớn của đời mình và của cả dòng tộc.",
        "Dù phu quân có đang bệnh nặng, nàng nguyện toàn tâm toàn ý chăm sóc ngày đêm, một lòng vì gia môn mà không hề oán thán nửa lời.",
        "Câu trả lời thấu tình đạt lý, vừa giữ trọn đạo hiếu vừa thể hiện khí chất đại gia đình khiến Lão phu nhân vô cùng xúc động và hài lòng.",
        [(1005.0, 1018.0), (1022.0, 1035.0), (1038.0, 1048.0)]
    ),
    (
        1050.0, 1100.0, "normal",
        "Lão tổ tông liền tháo ngay chiếc vòng ngọc bích gia truyền đeo vào cổ tay nàng, tuyên bố trước toàn thể gia quyến về của hồi môn mười dặm.",
        "Bảo rằng Thừa An Bá phủ tuyệt đối không để con cháu mình chịu thiệt thòi khi bước chân vào cửa nhà người khác, của cải mang theo sẽ trải dài mười dặm hồng trang.",
        "A Sửu quỳ lạy tạ ơn, trong lòng thầm nhủ phen này liều mạng đi làm dâu hào môn coi bộ cũng có thu hoạch bất ngờ ngoài mong đợi.",
        [(1055.0, 1068.0), (1072.0, 1085.0), (1088.0, 1098.0)]
    ),
    (
        1100.0, 1150.0, "serious",
        "Trái ngược với niềm hân hoan của Lão phu nhân, Bá phu nhân ngồi bên cạnh lại có biểu cảm vô cùng gượng gạo và bất an.",
        "Ánh mắt bà ta nhìn A Sửu chứa chan nỗi bàng hoàng lẫn xót xa, bàn tay lần tràng hạt run rẩy không ngừng phát ra tiếng lách cách.",
        "Dường như trong sâu thẳm tâm can, người đàn bà này đang che giấu một bí mật tội lỗi khủng khiếp liên quan đến thân thế thật sự của hai đứa trẻ.",
        [(1105.0, 1118.0), (1122.0, 1135.0), (1138.0, 1148.0)]
    ),
    (
        1150.0, 1200.0, "suspense",
        "Sau buổi thỉnh an, Bá phu nhân kéo Quân Đại vào phòng kín tra hỏi gắt gao về nguồn gốc thực sự của cô gái đang đóng giả tiểu thư.",
        "Quân Đại bực bội gạt phắt đi, bảo rằng mẹ chỉ cần biết con gái ruột của mẹ không phải đi làm góa phụ chịu khổ là được rồi.",
        "Ả ta còn dằn mặt mẹ mình không được can thiệp vào chuyện này, nếu phá hỏng kế hoạch thì cả phủ sẽ phải gánh tội khi quân lừa dối hoàng gia.",
        [(1155.0, 1168.0), (1172.0, 1185.0), (1188.0, 1198.0)]
    ),
    (
        1200.0, 1250.0, "punchline",
        "Bá phu nhân rơi nước mắt nghẹn ngào thốt lên rằng nếu có nhân quả báo ứng thì gia đình này sẽ gánh chịu muôn đời muôn kiếp.",
        "Quân Đại cười khẩy đáp lại rằng trên đời này làm gì có nhân quả, kẻ nào nắm được quyền lực và vàng bạc thì kẻ đó mới là chân lý sống.",
        "Đúng là tư duy của nhân vật phản diện điển hình, càng tự tin bao nhiêu thì sau này nghiệp quật sẽ càng đau đớn bấy nhiêu.",
        [(1205.0, 1218.0), (1222.0, 1235.0), (1238.0, 1248.0)]
    ),

    # 26 - 30: Chuẩn bị đại hôn & Cảnh chia tay
    (
        1250.0, 1300.0, "normal",
        "Thời gian thấm thoát trôi qua, ngày lành tháng tốt tổ chức hôn lễ xung hỷ cuối cùng cũng đã điểm trên tấm lịch treo tường.",
        "Cả Thừa An Bá phủ giăng đèn kết hoa đỏ rực rỡ, tiếng chiêng trống nhạc hỷ vang vọng khắp các ngõ phố trung tâm kinh thành náo nhiệt.",
        "Bên trong khuê phòng, A Sửu đang được các bà mối và cung nữ kỳ cựu trang điểm chải chuốt cẩn thận từng lọn tóc mượt mà.",
        [(1255.0, 1268.0), (1272.0, 1285.0), (1288.0, 1298.0)]
    ),
    (
        1300.0, 1350.0, "excited",
        "Bộ giá y màu đỏ son thêu hoa văn chim phượng bằng chỉ vàng lộng lẫy ôm trọn lấy vóc dáng thon thả kiều diễm của nàng tân nương.",
        "Khuôn mặt được dặm phấn thoa son tinh tế, làm nổi bật đôi mắt phượng sắc sảo và làn môi son quyến rũ hút hồn người đối diện.",
        "Đến lúc này, không còn ai có thể nhận ra bóng dáng của một cô gái nghèo từng lam lũ mưu sinh nơi ngõ hẻm lầy lội ngày nào.",
        [(1305.0, 1318.0), (1322.0, 1335.0), (1338.0, 1348.0)]
    ),
    (
        1350.0, 1400.0, "serious",
        "Quân Đại đứng bên cạnh nhìn ngắm bản sao hoàn mỹ của mình mà trong lòng dâng trào muôn vàn cảm xúc hỗn độn khó tả.",
        "Ả tiến lại gần, tự tay chỉnh lại chiếc khăn trùm đầu màu đỏ thêu hoa sen rồi ghé sát vào tai A Sửu thì thầm những lời đe dọa sắc lạnh.",
        "Bảo rằng khi bước qua cánh cổng phủ Anh Quốc Công, sống hay chết đều phụ thuộc vào sự kín miệng và ngoan ngoãn của nàng.",
        [(1355.0, 1368.0), (1372.0, 1385.0), (1388.0, 1398.0)]
    ),
    (
        1400.0, 1450.0, "normal",
        "A Sửu khẽ mỉm cười đáp lễ, ánh mắt không hề nao núng hay sợ hãi trước sự uy hiếp của nàng tiểu thư kênh kiệu độc ác.",
        "Nàng bình thản nhắc nhở Quân Đại hãy nhớ giữ đúng lời hứa gửi thuốc thang và tiền trợ cấp đều đặn về cho mẹ nuôi ở quê nhà.",
        "Hai người phụ nữ trao nhau cái nhìn đầy ẩn ý, một cuộc đổi vai lịch sử chính thức bắt đầu chuyển bánh không thể đảo ngược.",
        [(1405.0, 1418.0), (1422.0, 1435.0), (1438.0, 1448.0)]
    ),
    (
        1450.0, 1500.0, "suspense",
        "Khăn voan đỏ buông xuống che khuất dung nhan diễm lệ, A Sửu bước từng bước vững chãi ra khỏi khuê phòng hướng về phía cổng lớn.",
        "Mỗi bước chân đi là một lần nàng bỏ lại sau lưng quá khứ bần hàn tăm tối để tiến về phía tương lai mịt mờ nhưng đầy hứa hẹn.",
        "Tiếng pháo nổ giòn giã ngoài ngõ hòa cùng tiếng reo hò của đám đông đứng xem náo nhiệt dọc hai bên đường cái quan.",
        [(1455.0, 1468.0), (1472.0, 1485.0), (1488.0, 1498.0)]
    ),

    # 31 - 35: Lên kiệu hoa & Hành trình rước dâu
    (
        1500.0, 1550.0, "excited",
        "Chiếc kiệu hoa tám người khiêng lộng lẫy thêu rồng phượng nâng bổng nàng tân nương lên không trung trong sự kính cẩn của đoàn tùy tùng.",
        "Phía sau là hàng trăm rương hòm của cải sính lễ trải dài đúng mười dặm như lời hứa son sắt của Lão phu nhân dòng họ Thừa An Bá.",
        "Người dân kinh thành đổ xô ra đường trầm trồ thán phục trước độ chịu chơi và gia thế hiển hách của mối lương duyên danh gia vọng tộc.",
        [(1505.0, 1518.0), (1522.0, 1535.0), (1538.0, 1548.0)]
    ),
    (
        1550.0, 1600.0, "punchline",
        "Người ngoài nhìn vào cứ ngỡ đây là đám cưới thế kỷ trong mơ, đâu ai ngờ bên trong kiệu hoa là một cú lừa ngoạn mục thế kỷ.",
        "Cô dâu thật thì đang trốn trong phủ uống trà ăn bánh, còn cô dâu giả thì đang ngồi thẳng lưng chuẩn bị vào hang cọp bắt cọp con.",
        "A Sửu khẽ vén một góc rèm kiệu nhìn ra phố xá tấp nập, tự nhủ lòng mình nhất định phải sống sót trở về trong vinh quang rực rỡ.",
        [(1555.0, 1568.0), (1572.0, 1585.0), (1588.0, 1598.0)]
    ),
    (
        1600.0, 1650.0, "suspense",
        "Đoàn rước dâu dần dần tiến về phía phủ Anh Quốc Công uy nghiêm, nơi cánh cổng sắt sơn son khổng lồ đang từ từ mở rộng đón khách.",
        "Không khí ở đây tĩnh mịch và trang nghiêm hơn hẳn, không có tiếng cười đùa rộn rã mà chỉ thoang thoảng mùi thuốc bắc nồng nặc trong gió.",
        "Dấu hiệu cho thấy tình trạng nguy kịch của vị thế tử nằm bên trong đúng là không hề được phóng đại một chút nào cả.",
        [(1605.0, 1618.0), (1622.0, 1635.0), (1638.0, 1648.0)]
    ),
    (
        1650.0, 1700.0, "serious",
        "Kiệu hoa hạ xuống trước bậc tam cấp thềm rồng, bà mối đỡ tân nương bước qua chậu than hồng rực lửa theo phong tục xua đuổi tà ma xui xẻo.",
        "Từng nghi lễ bái đường được cử hành nhanh chóng và gấp gáp dưới sự chứng kiến của các vị bô lão và quan khách hai họ môn đăng hộ đối.",
        "Tất cả đều nơm nớp lo sợ thế tử tắt thở giữa chừng thì đám cưới biến thành đám tang ngay trong nháy mắt đầy bi thảm.",
        [(1655.0, 1668.0), (1672.0, 1685.0), (1688.0, 1698.0)]
    ),
    (
        1700.0, 1750.0, "normal",
        "A Sửu được đưa thẳng vào phòng tân hôn u tối, nơi chiếc giường gỗ lim chạm khắc tinh xảo đang buông rèm lụa dày đặc.",
        "Trên giường, một chàng trai tuấn tú với gương mặt góc cạnh đang nằm bất động, sắc mặt nhợt nhạt không một giọt máu tươi.",
        "Đó chính là Lục Trạc, vị chiến thần lẫy lừng sa trường nay lại phải chịu cảnh nằm liệt một chỗ chờ ngày số mệnh an bài.",
        [(1705.0, 1718.0), (1722.0, 1735.0), (1738.0, 1748.0)]
    ),

    # 36 - 40: Đêm tân hôn & Cú lật kèo bất ngờ
    (
        1750.0, 1800.0, "suspense",
        "Gia nhân và bà mối sau khi hoàn tất các thủ tục giao bôi hình thức liền vội vã lui hết ra ngoài, khóa chặt then cửa phòng lại.",
        "Căn phòng tân hôn rộng lớn giờ đây chỉ còn lại hai con người xa lạ, một người hôn mê bất tỉnh và một người mang thân phận giả mạo.",
        "A Sửu tự tay vén chiếc khăn voan đỏ thêu phượng, thở phào nhẹ nhõm một hơi dài sau chuỗi giờ phút căng thẳng đến nghẹt thở.",
        [(1755.0, 1768.0), (1772.0, 1785.0), (1788.0, 1798.0)]
    ),
    (
        1800.0, 1850.0, "punchline",
        "Nàng tiến lại gần bàn trà, thong thả rót nước và bốc ngay một miếng bánh ngọt đưa vào miệng nhai ngon lành để lót dạ sau một ngày nhịn đói.",
        "Vừa ăn nàng vừa nhìn ngắm vị phu quân trên danh nghĩa, thầm nghĩ chàng thế tử này đẹp trai phong độ thế này mà chết yểu thì phí của trời quá.",
        "Dù sao thì việc xung hỷ cũng đã xong, nàng chỉ việc diễn tròn vai một người vợ hiền thảo để chờ ngày mẹ nuôi bình phục hoàn toàn.",
        [(1805.0, 1818.0), (1822.0, 1835.0), (1838.0, 1848.0)]
    ),
    (
        1850.0, 1900.0, "excited",
        "Nhưng đúng lúc A Sửu tiến lại gần mép giường định chỉnh lại chăn ấm cho phu quân, một bàn tay lạnh ngắt bất ngờ chộp lấy cổ tay nàng.",
        "Lực nắm mạnh như gọng kìm khiến nàng giật thót tim đánh rơi cả chiếc khăn tay thêu hoa sen xuống đất.",
        "Đôi mắt sâu thẳm của Lục Trạc khẽ mở ra, ánh nhìn sắc bén như lưỡi gươm báu lập tức chiếu thẳng vào khuôn mặt của nàng tân nương.",
        [(1855.0, 1868.0), (1872.0, 1885.0), (1888.0, 1898.0)]
    ),
    (
        1900.0, 1950.0, "suspense",
        "Chàng thế tử tưởng chừng sắp đi gặp tổ tiên nay lại thần kỳ hồi tỉnh ngay trong đêm tân hôn định mệnh đầu tiên.",
        "Khí tức lạnh lẽo bao trùm khắp căn phòng khi chàng cất giọng khàn đặc hỏi rằng nàng rốt cuộc là ai và do ai phái đến đây ám hại chàng.",
        "A Sửu sững sờ trong giây lát, nhưng bản năng sinh tồn mãnh liệt của một cô gái lăn lộn giang hồ lập tức phát huy tác dụng kịp thời.",
        [(1905.0, 1918.0), (1922.0, 1935.0), (1938.0, 1948.0)]
    ),
    (
        1950.0, 2000.0, "serious",
        "Nàng không hề luống cuống run rẩy, trái lại nhẹ nhàng đỡ chàng ngồi dựa vào thành giường và rót ngay một chén nước ấm đưa tới tận miệng.",
        "Nàng từ tốn đáp rằng thiếp là thê tử hợp pháp được Thừa An Bá phủ gả sang để chăm sóc chàng, xin thế tử bớt giận giữ gìn long thể.",
        "Sự bình thản và điềm tĩnh khác thường của nàng thê tử mới cưới khiến vị thế tử đa nghi bắt đầu dấy lên mối hoài nghi sâu sắc trong lòng.",
        [(1955.0, 2018.0), (2022.0, 2035.0), (2038.0, 2048.0)]
    ),

    # 41 - 45: Diễn biến tiếp theo & Cục diện giằng co
    (
        2000.0, 2050.0, "normal",
        "Lục Trạc uống cạn chén nước ấm, ánh mắt vẫn không rời khỏi từng nét mặt và biểu cảm nhỏ nhất của người con gái đang đứng trước mặt mình.",
        "Chàng nhận ra đôi bàn tay của nàng tuy được bôi phấn trắng mịn nhưng khớp ngón tay lại có vết chai sạn của người từng lao động vất vả lâu năm.",
        "Một thiên kim tiểu thư sống trong nhung lụa ăn sung mặc sướng từ nhỏ tuyệt đối không thể nào có đôi bàn tay chai sần như thế này được.",
        [(2055.0, 2068.0), (2072.0, 2085.0), (2088.0, 2098.0)]
    ),
    (
        2050.0, 2100.0, "punchline",
        "A Sửu tinh ý nhận ra chàng đang soi xét bàn tay mình, liền nhanh trí giả vờ ngượng ngùng giấu tay vào trong ống tay áo rộng thùng thình.",
        "Nàng chống chế rằng dạo gần đây nàng thường xuyên chép kinh Phật và thêu khăn tay cầu nguyện cho thế tử nên ngón tay mới bị chai như vậy.",
        "Lý do nghe thì có vẻ hợp lý và tràn ngập tình nghĩa phu thê, nhưng trong bụng chàng thế tử thì thừa biết nàng đang bốc phét không chớp mắt.",
        [(2105.0, 2118.0), (2122.0, 2135.0), (2138.0, 2148.0)]
    ),
    (
        2100.0, 2150.0, "suspense",
        "Bên ngoài cửa sổ, bóng của một tỳ nữ thân tín do phủ Anh Quốc Công cài cắm đang lén lút dòm ngó nghe ngóng động tĩnh bên trong.",
        "Nhận thấy có kẻ rình rập, Lục Trạc bất ngờ kéo mạnh A Sửu ngã vào lòng mình trên chiếc giường hỷ phủ đầy cánh hoa hồng thơm ngát.",
        "Hành động táo bạo và bất ngờ của phu quân khiến A Sửu đỏ bừng mặt, tim đập thình thịch như đánh trống trận trong lồng ngực.",
        [(2155.0, 2168.0), (2172.0, 2185.0), (2188.0, 2198.0)]
    ),
    (
        2150.0, 2200.0, "excited",
        "Chàng ghé sát tai nàng thì thầm ra lệnh rằng hãy phối hợp diễn một màn kịch ân ái mặn nồng để đánh lạc hướng tai mắt của kẻ thù xung quanh.",
        "Hiểu được tình thế nguy hiểm ngàn cân treo sợi tóc, A Sửu lập tức hùa theo, cất tiếng nũng nịu ngọt ngào như rót mật vào tai chàng thế tử.",
        "Kẻ theo dõi bên ngoài nghe thấy động tĩnh thân mật liền vội vã rút lui trong đêm để về bẩm báo lại cho chủ mưu đứng sau giật dây.",
        [(2205.0, 2218.0), (2222.0, 2235.0), (2238.0, 2248.0)]
    ),
    (
        2200.0, 2250.0, "serious",
        "Khi kẻ địch đã đi xa, hai người lập tức tách nhau ra giữ khoảng cách an toàn, ánh mắt nhìn nhau chứa chan sự đề phòng và tính toán sâu xa.",
        "Một liên minh bất đắc dĩ giữa chàng thế tử trùng sinh hồi phục và nàng thiên kim giả mạo xuất thân đáy xã hội chính thức được thiết lập.",
        "Cả hai đều có những bí mật động trời cần che giấu và những kẻ thù nguy hiểm đang rình rập muốn dồn họ vào chỗ chết không toàn thây.",
        [(2255.0, 2268.0), (2272.0, 2285.0), (2288.0, 2298.0)]
    ),

    # 46 - 50: Hồi tưởng & Thân thế thật sự
    (
        2250.0, 2300.0, "normal",
        "Cùng lúc đó tại Thừa An Bá phủ, Quân Đại sau khi trút được gánh nặng hôn sự xung hỷ thì đang ung dung ngồi thưởng thức trà thơm bánh ngọt.",
        "Ả ta đắc ý cho rằng nước cờ của mình quá hoàn hảo, vừa giữ được thanh xuân trinh trắng vừa đuổi được kẻ có gương mặt giống mình đi xa xứ.",
        "Nhưng người tính không bằng trời tính, ả không thể ngờ rằng việc đẩy A Sửu đi chính là nhát dao tự chặt đứt vận mệnh tương lai của chính mình.",
        [(2305.0, 2318.0), (2322.0, 2335.0), (2338.0, 2348.0)]
    ),
    (
        2300.0, 2350.0, "suspense",
        "Trong căn phòng thờ gia tộc u ám, Bá phu nhân quỳ sụp trước bài vị tổ tiên khóc lóc thảm thiết vì nỗi dằn vặt tội lỗi bao năm chôn giấu.",
        "Ký ức mười sáu năm trước hiện về như một cuốn phim quay chậm: cảnh tượng tráo đổi hai đứa trẻ sơ sinh trong một đêm mưa gió bão bùng.",
        "Đứa trẻ mang dòng máu chính thống của Thừa An Bá phủ thực chất chính là Ngụy Nhiêu, tức A Sửu cô gái dọn đêm nghèo khổ ngày nay.",
        [(2355.0, 2368.0), (2372.0, 2385.0), (2388.0, 2398.0)]
    ),
    (
        2350.0, 2400.0, "serious",
        "Còn Quân Đại, đứa con gái được cưng chiều như ngọc như ngà bao năm qua thực chất chỉ là đứa con hoang của bà cô bên ngoại tráo vào nhận vơ danh phận.",
        "Bá phu nhân run rẩy lo sợ một ngày nào đó sự thật bị phơi bày ra ánh sáng, gia tộc sẽ tan nát và bản thân bà sẽ không còn mặt mũi nào nhìn tổ tiên.",
        "Bi kịch trớ trêu thay khi chính tay kẻ giả mạo lại tống khứ người thừa kế hợp pháp chân chính vào vòng tay của vị thế tử quyền lực nhất thiên hạ.",
        [(2405.0, 2418.0), (2422.0, 2435.0), (2438.0, 2448.0)]
    ),
    (
        2400.0, 2450.0, "punchline",
        "Đúng là người tính không bằng trời tính, tưởng đâu đẩy người ta vào chỗ chết ai ngờ lại tạo cơ hội cho chân phụng hoàng tái sinh từ tro tàn.",
        "Khán giả xem đến đây chỉ biết vỗ đùi đánh đét vì màn biên kịch quay xe quá gắt, quả báo đến muộn nhưng chắc chắn sẽ đến nơi đến chốn.",
        "Tập 1 kết thúc việc thiết lập bàn cờ một cách xuất sắc, mở đường cho những màn cung đấu trả thù rực lửa ở những tập tiếp theo.",
        [(2455.0, 2468.0), (2472.0, 2485.0), (2488.0, 2498.0)]
    ),
    (
        2450.0, 2500.0, "normal",
        "Sáng hôm sau, tin tức thế tử Anh Quốc Công hồi tỉnh thần kỳ sau đêm tân hôn lập tức lan truyền khắp toàn bộ kinh thành như một cơn lốc xoáy.",
        "Ai nấy đều trầm trồ ca tụng nhị tiểu thư Thừa An Bá phủ quả nhiên mang số mệnh đại cát đại lợi, vừa bước vào cửa là mang lại sinh khí dồi dào.",
        "Tin lành bay về Thừa An Bá phủ khiến Quân Đại đang ăn điểm tâm nghe xong mà sặc trà suýt nghẹn chết vì kinh hoàng tột độ.",
        [(2505.0, 2518.0), (2522.0, 2535.0), (2538.0, 2548.0)]
    ),

    # 51 - 55: Cao trào & Những toan tính mới
    (
        2500.0, 2550.0, "excited",
        "Ả ta bàng hoàng nhận ra mình vừa tự tay dâng tặng vị trí thế tử phi quyền quý và người chồng đẹp trai tài giỏi cho một đứa dọn đêm hèn hạ.",
        "Cơn ghen tức và hối hận trào dâng trong lòng khiến Quân Đại phát điên, lập tức toan tính mưu kế mới để tìm cách lật tẩy và triệt hạ A Sửu.",
        "Từ vị thế kẻ chủ động ban phát số phận, nay ả ta đã biến thành kẻ thua cuộc nơm nớp lo sợ bị lật ngược tình thế bất cứ lúc nào.",
        [(2555.0, 2568.0), (2572.0, 2585.0), (2588.0, 2598.0)]
    ),
    (
        2550.0, 2600.0, "serious",
        "Trong khi đó tại Anh Quốc Công phủ, A Sửu bắt đầu đón nhận sự kính trọng từ gia nhân và sự chào đón nồng nhiệt của các bậc trưởng bối trong phủ.",
        "Nàng không hề tự mãn hay kiêu ngạo, trái lại vẫn giữ thái độ khiêm nhường, cẩn trọng trong từng lời ăn tiếng nói và cử chỉ thường nhật.",
        "Sự khôn ngoan và tinh tế của nàng nhanh chóng chiếm trọn cảm tình của Lão phu nhân nhà chồng, củng cố vững chắc vị thế trong gia tộc.",
        [(2605.0, 2618.0), (2622.0, 2635.0), (2638.0, 2648.0)]
    ),
    (
        2600.0, 2650.0, "suspense",
        "Lục Trạc quan sát người vợ mới cưới suốt cả ngày trời, càng nhìn càng nhận thấy nàng có khí chất bất phàm và bản lĩnh kiên cường hiếm có.",
        "Chàng biết thân thế của nàng chắc chắn có uẩn khúc lớn, nhưng tạm thời chàng quyết định giữ im lặng để xem nàng sẽ diễn tiếp màn kịch này ra sao.",
        "Mối quan hệ giữa hai người dần chuyển từ đối đầu nghi ngờ sang sự tôn trọng và thấu hiểu ngầm trong từng ánh mắt trao nhau.",
        [(2655.0, 2668.0), (2672.0, 2685.0), (2688.0, 2698.0)]
    ),
    (
        2650.0, 2700.0, "normal",
        "Những dòng người tấp nập kéo đến chúc mừng đôi tân lang tân nương mang lại sinh khí rộn ràng khắp phủ đệ sau chuỗi ngày ảm đạm dài dằng dặc.",
        "Nhạc hỷ lại một lần nữa trỗi khúc hân hoan, báo hiệu một chương mới rực rỡ sắp sửa mở ra cho số phận của cô gái từng mang tên A Sửu.",
        "Từ đáy bùn đen xã hội bước lên đỉnh cao danh vọng, hành trình của nàng chỉ mới bắt đầu nhưng đã mang đầy dáng dấp của một truyền kỳ.",
        [(2705.0, 2718.0), (2722.0, 2735.0), (2738.0, 2748.0)]
    ),
    (
        2700.0, 2750.0, "punchline",
        "Cái giá của chiếc trâm vàng năm xưa nay đã được quy đổi bằng cả một cuộc đời mới, nơi kẻ ác phải run sợ còn người lương thiện được đền đáp.",
        "Quân Đại đứng từ xa nhìn cỗ xe ngựa quyền quý đi qua mà cắn nát môi dưới, chính thức tuyên chiến trong bóng tối với người chị em sinh đôi.",
        "Cuộc chiến sinh tử giữa hai đóa hoa song sinh cùng chung gương mặt nhưng khác biệt tâm can hứa hẹn sẽ làm nổ tung màn ảnh trong các tập tiếp theo.",
        [(2755.0, 2768.0), (2772.0, 2785.0), (2788.0, 2798.0)]
    ),

    # 56 - 59: Khép lại diễn biến tập 1 & Nhạc kết
    (
        2750.0, 2800.0, "excited",
        "Tập 1 của Gả Kim Thoa khép lại bằng phân cảnh Lục Trạc mỉm cười đưa tay đỡ A Sửu bước xuống bậc thềm trước sự chứng kiến của toàn thể bá quan.",
        "Ánh nắng ban mai rực rỡ chiếu rọi lên tà áo đỏ thêu hoa phượng của nàng thế tử phi mới, rạng ngời và kiêu hãnh như một nữ vương thực thụ.",
        "Một cái kết không thể nào viên mãn hơn cho tập mở màn, vừa thỏa mãn tâm lý người xem vừa gieo rắc vô số sự tò mò háo hức khôn nguôi.",
        [(2805.0, 2818.0), (2822.0, 2835.0), (2838.0, 2848.0)]
    ),
    (
        2800.0, 2850.0, "normal",
        "Tiếng hát hào hùng đầy bi tráng của bài ca chủ đề Tá Danh Nhập Cục do Lưu Vũ Ninh thể hiện vang lên đưa tập phim dần đi vào hồi kết.",
        "Từng lời ca da diết như khắc họa trọn vẹn số phận nghiệt ngã của những kiếp người tráo đổi thân phận trong vòng xoáy quyền mưu tranh đoạt.",
        "Một bộ phim cổ trang cung đấu xuất sắc hiếm hoi của năm nay mà mọt phim chân chính tuyệt đối không nên bỏ lỡ dù chỉ một giây.",
        [(2855.0, 2868.0), (2872.0, 2885.0), (2888.0, 2898.0)]
    ),
]

ASSESSMENT_TEXT = (
    "Tập một Gả Kim Thoa có nhịp phim nhanh gọn, mâu thuẫn thế gả thiết lập sắc nét và diễn xuất phân thân của Điền Hi Vi cực kỳ lôi cuốn. "
    "Màu phim sang trọng cùng âm nhạc hoành tráng tạo cảm giác điện ảnh rõ rệt. "
    "Đây chắc chắn là tác phẩm cổ trang gia đấu đáng xem nhất thời điểm hiện tại cho các mọt phim cung đấu."
)

def build():
    segments = []
    seg_id = 1
    for item in STORY_DATA:
        start, end, emo, text1, text2, text3 = item[0], item[1], item[2], item[3], item[4], item[5]
        narration = [
            SpeechUnit(id=f"u{seg_id}_1", text=text1, emotion=emo),
            SpeechUnit(id=f"u{seg_id}_2", text=text2, emotion=emo),
            SpeechUnit(id=f"u{seg_id}_3", text=text3, emotion="normal" if emo != "punchline" else "punchline"),
        ]
        
        # Tạo 3 shots phân bổ đều và an toàn trong khoảng [start, end]
        margin = 1.0
        available = (end - start) - (margin * 2)
        step = available / 3.0
        shots = [
            ReviewShot(
                source_start=round(start + margin + i * step, 2),
                source_end=round(start + margin + (i + 0.9) * step, 2),
                weight=1.0,
                speech_unit_id=narration[i].id
            )
            for i in range(3)
        ]
        
        segments.append(ReviewSegment(
            id=seg_id,
            section="story",
            source_start=start,
            source_end=end,
            narration=narration,
            shots=shots,
            visual_intent=f"Diễn biến tập 1 đoạn {start:.0f}s-{end:.0f}s",
            keep_original_audio=True
        ))
        seg_id += 1

    # Final Assessment segment: exactly 15s, section="assessment"
    segments.append(ReviewSegment(
        id=seg_id,
        section="assessment",
        source_start=2850.0,
        source_end=2912.15,
        narration=ASSESSMENT_TEXT,
        shots=[
            ReviewShot(source_start=2855.0, source_end=2875.0),
            ReviewShot(source_start=2880.0, source_end=2905.0),
        ],
        visual_intent="Đánh giá tổng quan chất lượng diễn xuất, kịch bản và màu phim tập 1",
        keep_original_audio=False
    ))

    script = ReviewScript(
        title="Gả Kim Thoa Tập 1 — Kèo Thơm Xung Hỷ Và Cú Lội Ngược Dòng Của Nàng Đổ Dạ Hương",
        source_video="input/videos/ga_kim_thoa_ep01.mp4",
        segments=segments
    )

    out_file = ROOT / "input" / "scripts" / "review.ga_kim_thoa_ep01.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(script.model_dump_json(indent=2), encoding="utf-8")
    print(f"Generated {len(segments)} segments -> {out_file}")

    # Validate load
    loaded = ReviewScript.load(out_file)
    words = sum(len(u.text.split()) for s in loaded.segments for u in (s.narration if isinstance(s.narration, list) else [SpeechUnit(text=s.narration)]))
    print(f"Validated successfully! Total segments: {len(loaded.segments)}, Total words: {words}")

if __name__ == "__main__":
    build()
