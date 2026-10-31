"""
Generate enriched review.ga_kim_thoa_ep01.json with ~6,850 total words
to achieve ~1,305s duration (44.8% of source duration 2912.15s),
matching the 40-50% editorial target with extreme precision.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline.schema import ReviewScript, ReviewSegment, ReviewShot
from src.audio.speech import SpeechUnit

# 64 Story segments with rich commentary (~105-110 words per segment)
ENRICHED_STORY = [
    # 1
    (
        0.0, 44.53, "normal",
        "Vừa mở màn, siêu phẩm cổ trang gia đấu Gả Kim Thoa đã ném khán giả vào ngay bầu không khí nhung lụa xa hoa nhưng ngập tràn mưu mô toan tính của Thừa An Bá phủ.",
        "Tại khuê phòng lộng lẫy, nhị tiểu thư Quân Đại kiêu kỳ đang ngồi trước gương đồng, tay mân mê chiếc trâm vàng nạm ngọc gia truyền với nụ cười tự mãn vô cùng đắc ý.",
        "Cứ ngỡ nàng ta sắp sửa danh chính ngôn thuận bước chân vào hào môn danh giá bậc nhất kinh thành để mặc sức hưởng trọn vinh hoa phú quý muôn đời."
    ),
    # 2
    (
        44.53, 89.06, "punchline",
        "Nhưng đời đúng là không như là mơ, tin tức sét đánh từ tiền sảnh truyền vào khiến nụ cười trên môi nàng tiểu thư lập tức tắt ngúm trong một nốt nhạc ngắn ngủi.",
        "Hôn ước từ thuở ấu thơ của nàng đúng là môn đăng hộ đối thật sự, đối tượng kết duyên chính là Lục Trạc, vị thế tử phủ Anh Quốc Công lừng lẫy uy phong.",
        "Ngặt nỗi chàng thế tử vừa đánh trận trở về thì chẳng may trúng tên độc, hiện đang nằm bất tỉnh nhân sự, hơi thở thoi thóp mong manh như ngọn đèn dầu trước cơn bão lớn."
    ),
    # 3
    (
        89.06, 133.59, "suspense",
        "Phủ Anh Quốc Công thấy đứa con trai độc nhất sắp sửa đi gặp diêm vương liền nảy ra sáng kiến tổ chức đám cưới gấp gáp để xung hỷ xua đuổi tà ma xui xẻo.",
        "Nói toạc móng heo ra là muốn rước Quân Đại về để nếu thế tử có mệnh hệ nào thì nàng sẽ lập tức trở thành góa phụ tiết hạnh giữ trọn trinh tiết suốt cả cuộc đời.",
        "Nàng tiểu thư kiêu kỳ cành vàng lá ngọc nghe xong thì giãy nảy như đỉa phải vôi, một mực cự tuyệt bước chân vào nấm mồ hôn nhân định mệnh đầy tăm tối này."
    ),
    # 4
    (
        133.59, 178.12, "excited",
        "Nàng gào thét long trời lở đất trong phòng, đập phá tan tành đồ đạc và tuyên bố thẳng thừng rằng thà cạo đầu làm ni cô chứ quyết không lấy một khúc gỗ mục bất động.",
        "Thế nhưng hôn ước hoàng gia là do Lão tổ tông và triều đình đích thân định đoạt, đâu phải thứ muốn quỵt là quỵt được dễ dàng như ăn một chiếc kẹo đường.",
        "Trong lúc tranh cãi nảy lửa đến nghẹt thở với tỳ nữ thân cận, chiếc trâm cài tóc vàng ròng đắt giá bất ngờ tuột khỏi tay rơi choảng xuống nền sàn gạch lạnh lẽo."
    ),
    # 5
    (
        178.12, 222.66, "serious",
        "Đầu trâm sắc nhọn vấy lên một vệt máu đỏ tươi chói mắt, báo hiệu chuỗi sóng gió quyền mưu kinh thiên động địa sắp sửa đổ ập xuống cả gia tộc.",
        "Bị dồn vào chân tường không lối thoát, Quân Đại bắt đầu vận dụng hết công suất chất xám trong đầu để ráo riết tìm đường thoát thân cho bằng được.",
        "Và rồi, một kế hoạch tráo mận đổi đào điên rồ và táo bạo nhất chốn kinh kỳ đã được nàng ta âm thầm vạch ra từng đường đi nước bước trong bóng tối."
    ),
    # 6
    (
        222.66, 267.19, "normal",
        "Rời khỏi khu phủ đệ nguy nga tráng lệ, ống kính máy quay lập tức chuyển cảnh sang một góc ngõ hẻm nghèo nàn, lầy lội và hôi hám ở khu vực ngoại thành xa xôi.",
        "Tại đây, một cô gái trẻ trong bộ đồ vải thô rách rưới đang còng lưng gánh từng thùng dạ hương nặng trĩu đi đổ thuê kiếm từng đồng bạc cắc mưu sinh qua ngày.",
        "Dù mặt mũi lấm lem bùn đất và phải làm công việc bần hàn nhất thiên hạ, nhưng đôi mắt trong veo của cô gái vẫn sáng ngời và tràn đầy nghị lực phi thường."
    ),
    # 7
    (
        267.19, 311.72, "punchline",
        "Cô nàng này tên gọi là A Sửu, cái tên xấu xí người ta đặt cho để mong dễ nuôi, nhưng thực chất dung mạo ẩn sau lớp nhọ nồi lại là một tuyệt sắc giai nhân nghiêng nước nghiêng thành.",
        "Điều kỳ lạ hơn nữa là nếu rửa sạch lớp bùn đất lem luốc, A Sửu sở hữu ngũ quan thanh tú giống nhị tiểu thư Quân Đại như hai giọt nước đúc ra từ cùng một khuôn mẫu.",
        "Khán giả xem phim đến đây là ngửi thấy ngay mùi vị của thân thế tráo con từ thuở mới lọt lòng vô cùng quen thuộc của dòng phim gia đấu kinh điển rồi."
    ),
    # 8
    (
        311.72, 356.25, "suspense",
        "A Sửu cày cuốc ngày đêm không quản mưa nắng không phải vì đam mê lao động công ích, mà vì người mẹ nuôi đang mắc bạo bệnh hiểm nghèo nằm liệt giường trong túp lều rách nát.",
        "Tiền thuốc men đắt đỏ mỗi ngày như muối bỏ bể, chủ tiệm thuốc liên tục cho người đến xiết nợ khiến hai mẹ con rơi vào bước đường cùng tăm tối không lối thoát.",
        "Đúng vào thời khắc tuyệt vọng nhất của số phận thì một cỗ xe ngựa sang trọng lộng lẫy bất ngờ dừng lại ngay trước đầu con hẻm ổ chuột tối tăm hôi hám."
    ),
    # 9
    (
        356.25, 400.78, "excited",
        "Quân Đại kiêu kỳ bước xuống xe, đưa khăn tay che mũi nhìn quanh với vẻ khinh bỉ tột cùng, nhưng khi nhìn thẳng vào mặt A Sửu thì ả ta chết trân tại chỗ không thốt nên lời.",
        "Sự giống nhau đến mức rợn người giữa hai số phận đối nghịch đã chứng minh cho ả thấy rằng chiếc phao cứu sinh duy nhất của đời mình đã xuất hiện đúng lúc.",
        "Quân Đại lập tức cho thị vệ đuổi hết dân tình xung quanh rồi kéo xộc A Sửu vào căn nhà tranh dột nát để bàn bạc một phi vụ làm ăn lớn làm thay đổi cả cuộc đời."
    ),
    # 10
    (
        400.78, 445.31, "serious",
        "Không vòng vo tam quốc dài dòng, nàng thiên kim ném ngay một bọc bạc trắng lấp lánh lên chiếc bàn gỗ ọp ẹp trước ánh mắt ngỡ ngàng tròn xoe của cô gái nghèo.",
        "Ả bảo rằng chỉ cần A Sửu chịu đóng giả làm nhị tiểu thư bước lên kiệu hoa gả sang phủ Anh Quốc Công xung hỷ, toàn bộ tiền thuốc thang và cuộc sống của mẹ sẽ được chu cấp trọn đời.",
        "Ngược lại, nếu dám từ chối hoặc để lộ nửa lời ra ngoài, cả hai mẹ con sẽ không còn đất dung thân ở cái kinh thành đầy rẫy tai vách mạch rừng và cạm bẫy chết người này."
    ),
    # 11
    (
        445.31, 489.84, "normal",
        "A Sửu cầm thỏi bạc nặng trịch trên tay mà cõi lòng trĩu nặng như đeo đá tảng, nàng thừa hiểu bước chân vào chốn hào môn sâu như biển chẳng khác nào tự nhảy vào miệng cọp dữ.",
        "Nhưng khi quay đầu nhìn mẹ nuôi đang ho sặc sụa từng cơn đau đớn trên manh chiếu rách, nàng biết mình không còn bất kỳ sự lựa chọn nào khác ngoài việc đem tính mạng ra đánh cược.",
        "Nàng ngẩng cao đầu dứt khoát đồng ý nhận lời giao dịch định mệnh, chính thức mở ra một bước ngoặt đổi đời đầy chông gai bão táp nhưng cũng vô cùng hiển hách."
    ),
    # 12
    (
        489.84, 534.38, "suspense",
        "Khi màn đêm đen kịt buông xuống kinh thành, một cỗ xe ngựa bí mật lặng lẽ đưa A Sửu luồn qua cửa sau hiểm hóc để tiến thẳng vào nội viện thâm sâu của Thừa An Bá phủ.",
        "Vừa cởi bỏ bộ đồ thô kệch lấm lem và tắm gội sạch sẽ bằng nước hoa hồng, dung nhan thực sự của nàng lộ ra khiến ngay cả đám tỳ nữ thân cận của Quân Đại cũng phải giật mình thảng thốt.",
        "Quân Đại đứng bên cạnh nhìn ngắm bản sao hoàn mỹ của mình mà vừa mừng rỡ vừa lo sợ, trong lòng dấy lên nỗi ghen ghét đố kỵ khó tả trước nét đẹp thanh thuần thoát tục của đối phương."
    ),
    # 13
    (
        534.38, 578.91, "punchline",
        "Khóa huấn luyện cấp tốc mang tên biến quạ thành phượng hoàng chính thức được kích hoạt ngay trong đêm tối tĩnh mịch với những kỷ luật thép vô cùng khắc nghiệt.",
        "Một cô gái vốn dĩ quen gánh phân bước đi thoăn thoắt ngoài ngõ giờ đây bị ép buộc phải học cách đi đứng thong thả nhẹ nhàng như hoa sen lướt trên mặt nước hồ thu.",
        "Đầu đội bát nước đầy ắp, sau lưng buộc thanh nẹp gỗ thẳng tắp, hễ làm sánh ra một giọt là bà quản sự lập tức dùng thước kẻ gõ mạnh vào tay cảnh cáo không chút thương tiếc."
    ),
    # 14
    (
        578.91, 623.44, "normal",
        "Thế nhưng điều khiến Quân Đại và đám gia nhân kinh ngạc tột độ là A Sửu tiếp thu cực kỳ nhanh nhạy, ngón tay búp măng cầm chiếc quạt lụa che nửa mặt duyên dáng đến lạ kỳ.",
        "Từng dáng đi uyển chuyển, nụ cười hé môi e ấp cho đến cái liếc mắt đưa tình của giới quý tộc đều được nàng nắm bắt và mô phỏng chuẩn xác đến từng chi tiết nhỏ nhất.",
        "Dường như cốt cách cao quý vốn dĩ đã nằm sẵn trong từng tế bào và dòng máu của nàng từ kiếp nào, chỉ chờ cơ hội ngàn năm có một này là bùng phát mạnh mẽ phi thường."
    ),
    # 15
    (
        623.44, 667.97, "serious",
        "Bên cạnh việc rèn giũa hình thể lễ nghi, Quân Đại còn bắt A Sửu học thuộc lòng gia phả dòng họ, tính cách sở thích và các mối quan hệ tranh quyền đoạt lợi phức tạp trong gia tộc.",
        "Từ thói quen uống trà sen sớm của Lão tổ tông cho đến tật xấu hay soi mói xét nét của các vị phu nhân đều phải ghi nhớ nằm lòng vanh vách không được phép sai sót nửa lời.",
        "Bởi vì trong chốn thâm cung hậu viện đầy cạm bẫy, chỉ cần sơ sẩy lộ ra một thói quen bần hàn nhỏ bé là đầu sẽ lập tức lìa khỏi cổ ngay tức khắc không kịp trăn trối."
    ),
    # 16
    (
        667.97, 712.50, "suspense",
        "Trong lúc tập luyện dâng trà bái lễ, tỳ nữ vô tình phát hiện trên cánh tay mềm mại của A Sửu có một vết sẹo dài do thời thơ ấu vất vả lao động kiếm sống để lại.",
        "Quân Đại hoảng hốt nhận ra tay tiểu thư khuê các mịn màng như ngọc không tì vết, nếu đêm tân hôn bị nhà trai phát hiện vết sẹo này thì màn kịch sẽ lộ tẩy hoàn toàn.",
        "Ả ta lập tức sai gia nhân mang bột phấn ngọc trai quý hiếm và cao mờ sẹo hảo hạng đến bôi trát nhiều lớp kỹ lưỡng nhằm ngụy trang tuyệt đối vết tích trên da thịt."
    ),
    # 17
    (
        712.50, 757.03, "excited",
        "A Sửu cắn chặt răng chịu đựng cảm giác đau rát buốt thấu xương khi lớp thuốc đặc trị bôi lên da thịt mà không hề hé môi kêu ca than vãn lấy một tiếng nào.",
        "Sự bình thản đến lạnh lùng và ánh mắt kiên định phi thường của cô gái nghèo khiến đám ma ma hầu cận bên cạnh bắt đầu nảy sinh sự kiêng dè và nể phục từ tận đáy lòng.",
        "Nàng hiểu rõ hơn ai hết rằng đây không chỉ đơn thuần là một màn kịch gả thay gánh nạn, mà còn là chiếc chìa khóa duy nhất giúp nàng vươn lên đổi thay số phận bèo bọt."
    ),
    # 18
    (
        757.03, 801.56, "normal",
        "Sáng hôm sau, hồi chuông báo hiệu giờ thỉnh an trang trọng vang vọng khắp các dãy hành lang rợp bóng cây cổ thụ trăm năm của Thừa An Bá phủ uy nghiêm.",
        "Đây chính là bài thi sát hạch sống còn đầu tiên: A Sửu phải trực tiếp diện kiến Lão tổ tông và mẫu thân trước khi chính thức khoác áo tân nương bước lên kiệu hoa.",
        "Quân Đại đứng nép mình sau tấm bình phong chạm trổ hoa điểu, mồ hôi túa ra ướt đẫm trán vì lo sợ kế hoạch tráo mận đổi đào bị vạch trần giữa thanh thiên bạch nhật."
    ),
    # 19
    (
        801.56, 846.09, "punchline",
        "A Sửu khoác lên mình bộ gấm hoa đỏ rực lộng lẫy, đầu cài trâm ngọc buông rủ lung linh, từng bước chân đoan trang tiến vào đại sảnh như một nàng tiên giáng trần đích thực.",
        "Điệu bộ dịu dàng thùy mị, lời nói dạ thưa nhỏ nhẹ lễ phép khiến ngay cả các vị ma ma khó tính khắt khe nhất trong phủ cũng phải gật gù hài lòng khen ngợi tấm tắc.",
        "Quân Đại nấp bên trong nhìn ra mà tức anh ách nghẹn họng, tự hỏi không hiểu con nhỏ gánh dạ hương này có uống nhầm thần dược quý tộc bí truyền ở nơi nào hay không."
    ),
    # 20
    (
        846.09, 890.62, "suspense",
        "Lão phu nhân ngồi uy nghiêm trên chiếc ghế bọc gấm nhung khẽ nhấp một ngụm trà thơm, đôi mắt tinh đời từng trải nheo lại quan sát từng cử chỉ nhỏ của đứa cháu gái yêu quý.",
        "Bà cụ đột nhiên cất tiếng gọi A Sửu bước lại gần rồi nắm chặt lấy bàn tay nàng, nhẹ nhàng ân cần hỏi han về những tâm tư cảm xúc trước ngày đại hôn xuất giá.",
        "Không khí trong toàn bộ đại sảnh bỗng chốc đông cứng lại như băng tuyết, ai nấy đều nín thở hồi hộp chờ đợi xem liệu có điều gì sơ hở bị phát giác hay không."
    ),
    # 21
    (
        890.62, 935.16, "excited",
        "Bằng sự nhạy bén và thông minh trời phú, A Sửu khéo léo đáp rằng được gả cho thế tử Anh Quốc Công là phúc phận lớn lao vô bờ của cuộc đời mình và cả dòng tộc.",
        "Dù phu quân hiện tại đang lâm trọng bệnh, nàng nguyện toàn tâm toàn ý chăm sóc ngày đêm không quản khó nhọc, một lòng vì gia môn mà không hề oán thán nửa lời.",
        "Câu trả lời thấu tình đạt lý, vừa giữ trọn đạo hiếu làm con vừa thể hiện khí chất đoan trang của tiểu thư khuê các khiến Lão phu nhân vô cùng xúc động và nở nụ cười mãn nguyện."
    ),
    # 22
    (
        935.16, 979.69, "normal",
        "Lão tổ tông liền tháo ngay chiếc vòng ngọc bích gia truyền đeo vào cổ tay nàng, dõng dạc tuyên bố trước toàn thể gia quyến về của hồi môn mười dặm hồng trang danh giá.",
        "Bà khẳng định Thừa An Bá phủ tuyệt đối không để con cháu dòng dõi chịu chút thiệt thòi nào khi bước chân sang cửa nhà người khác làm dâu hiền vợ thảo.",
        "A Sửu dập đầu quỳ lạy tạ ơn sâu nặng, trong lòng thầm nhủ phen này liều mạng đi làm dâu hào môn xung hỷ coi bộ cũng gặt hái được những món hời bất ngờ ngoài mong đợi."
    ),
    # 23
    (
        979.69, 1024.22, "serious",
        "Trái ngược hoàn toàn với niềm hân hoan rạng rỡ của Lão phu nhân, Bá phu nhân ngồi bên cạnh lại có sắc mặt vô cùng gượng gạo, tái mét và bất an tột độ.",
        "Ánh mắt bà ta nhìn xoáy vào A Sửu chứa chan nỗi bàng hoàng thảng thốt xen lẫn xót xa, những ngón tay lần tràng hạt run rẩy không ngừng phát ra tiếng lách cách nghẹt thở.",
        "Dường như trong sâu thẳm tâm can người đàn bà quý tộc này đang chôn giấu một bí mật tội lỗi khủng khiếp liên quan trực tiếp đến thân thế của hai đứa trẻ năm xưa."
    ),
    # 24
    (
        1024.22, 1068.75, "suspense",
        "Ngay sau khi buổi thỉnh an kết thúc, Bá phu nhân vội vã kéo Quân Đại vào phòng kín đóng chặt then cài, gắt gao tra hỏi về nguồn gốc xuất thân thực sự của cô gái lạ mặt kia.",
        "Quân Đại bực bội gạt phắt đi không thèm giải thích, lạnh lùng bảo rằng mẹ chỉ cần biết con gái ruột của mẹ không phải đi làm góa phụ chịu khổ nhục cả đời là đủ rồi.",
        "Ả ta còn buông lời đe dọa ngược lại mẹ mình không được phép can thiệp vào chuyện này, nếu làm hỏng kế hoạch thì cả gia đình sẽ phải gánh tội khi quân lừa dối hoàng thất."
    ),
    # 25
    (
        1068.75, 1113.28, "punchline",
        "Bá phu nhân rơi nước mắt nghẹn ngào trong cay đắng, thốt lên rằng nếu trên đời có luật nhân quả báo ứng thì dòng họ này sẽ gánh chịu muôn kiếp không ngày nào yên ổn.",
        "Quân Đại cười khẩy đầy kiêu ngạo đáp lại rằng trên cõi đời này làm gì có nhân quả công bằng, kẻ nào nắm trong tay quyền lực và vàng bạc thì kẻ đó mới nắm giữ chân lý sống.",
        "Đúng là tư duy thiển cận của một nhân vật phản diện kinh điển, càng tự đắc ngạo mạn bao nhiêu thì sau này khi nghiệp quật sẽ càng ê chề và đau đớn bấy nhiêu."
    ),
    # 26
    (
        1113.28, 1157.81, "normal",
        "Thời gian thấm thoát thoi đưa như bóng câu qua cửa sổ, ngày lành tháng tốt tổ chức hôn lễ xung hỷ trừ tà cuối cùng cũng đã điểm trên tấm lịch đỏ của phủ đệ.",
        "Cả Thừa An Bá phủ giăng đèn kết hoa đỏ rực rỡ từ trong ra ngoài, tiếng kèn tiếng trống nhạc hỷ vang vọng tưng bừng khắp các ngõ phố trung tâm kinh thành phồn hoa.",
        "Bên trong khuê phòng son rỗi, A Sửu đang được các bà mối và cung nữ kỳ cựu tỉ mỉ trang điểm chải chuốt cẩn thận từng lọn tóc mượt mà đen óng ả."
    ),
    # 27
    (
        1157.81, 1202.34, "excited",
        "Bộ giá y màu đỏ son thêu hoa văn chim phượng hoàng lộng lẫy bằng chỉ vàng kim ôm trọn lấy vóc dáng thon thả, uyển chuyển kiều diễm của nàng tân nương tuyệt sắc.",
        "Khuôn mặt thanh tú được dặm phấn thoa son tinh xảo, làm nổi bật đôi mắt phượng sắc bén thông minh cùng làn môi son quyến rũ hút trọn mọi ánh nhìn say đắm.",
        "Đến thời khắc này, không còn bất kỳ ai có thể nhận ra bóng dáng lam lũ của một cô gái nghèo từng gánh dạ hương mưu sinh nơi ngõ hẻm lầy lội ngày nào nữa."
    ),
    # 28
    (
        1202.34, 1246.88, "serious",
        "Quân Đại đứng bên cạnh ngắm nhìn bản sao hoàn mỹ đến không tì vết của mình mà trong lòng dâng trào muôn vàn cảm xúc hỗn độn vừa đắc ý vừa ghen ghét khó tả.",
        "Ả tiến lại thật gần, tự tay chỉnh sửa lại chiếc khăn trùm đầu màu đỏ thêu hoa sen rồi ghé sát vào tai A Sửu buông ra những lời đe dọa sắc lạnh như băng giá.",
        "Ả bảo rằng khi đã bước chân qua cánh cổng phủ Anh Quốc Công, việc sống hay chết, vinh hay nhục đều hoàn toàn phụ thuộc vào sự kín miệng và ngoan ngoãn của nàng."
    ),
    # 29
    (
        1246.88, 1291.41, "normal",
        "A Sửu khẽ mỉm cười nhẹ nhàng đáp lễ, ánh mắt trong veo không hề biểu lộ chút nao núng hay sợ hãi nào trước sự uy hiếp gay gắt của nàng tiểu thư kênh kiệu độc ác.",
        "Nàng bình thản nhắc nhở Quân Đại hãy luôn nhớ giữ đúng lời hứa gửi thuốc men thượng hạng và tiền trợ cấp sinh hoạt đều đặn về cho mẹ nuôi ở quê nhà chữa bệnh.",
        "Hai người phụ nữ trao nhau cái nhìn đầy ẩn ý và toan tính, một cuộc hoán đổi vai diễn lịch sử chính thức bắt đầu chuyển bánh không có đường quay đầu trở lại."
    ),
    # 30
    (
        1291.41, 1335.94, "suspense",
        "Tấm khăn voan đỏ thêu phượng buông xuống che khuất dung nhan diễm lệ, A Sửu bước từng bước chân vững chãi và tự tin ra khỏi khuê phòng hướng thẳng về phía cổng lớn.",
        "Mỗi bước chân nàng đi qua là một lần nàng bỏ lại sau lưng quá khứ bần hàn tăm tối để can trường tiến về phía tương lai mịt mờ phía trước nhưng đầy hứa hẹn bất ngờ.",
        "Tiếng pháo nổ vang trời giòn giã ngoài ngõ hòa cùng tiếng reo hò chúc tụng náo nhiệt của đám đông người dân đứng chen chúc chật kín hai bên đường cái quan."
    ),
    # 31
    (
        1335.94, 1380.47, "excited",
        "Chiếc kiệu hoa tám người khiêng lộng lẫy thêu rồng phượng nâng bổng nàng tân nương lên không trung trong sự kính cẩn nghiêm trang của toàn bộ đoàn tùy tùng rước dâu.",
        "Phía sau cỗ kiệu là hàng trăm rương hòm của cải sính lễ vàng bạc gấm vóc trải dài đúng mười dặm hồng trang như lời hứa son sắt của Lão phu nhân dòng họ Thừa An Bá.",
        "Dân chúng khắp kinh thành đổ xô ra đường trầm trồ thán phục không ngớt trước độ chịu chơi xa hoa và gia thế hiển hách tột bậc của mối lương duyên danh gia vọng tộc này."
    ),
    # 32
    (
        1380.47, 1425.00, "punchline",
        "Người ngoài nhìn vào cứ ngỡ đây là một đám cưới thế kỷ trong mơ ngập tràn hạnh phúc, đâu ai ngờ sâu bên trong kiệu hoa lại là một cú lừa ngoạn mục chấn động lịch sử.",
        "Cô dâu danh chính ngôn thuận thì đang trốn chui trốn lủi trong phòng uống trà ăn điểm tâm, còn cô dâu giả mạo thì đang ngồi thẳng lưng hiên ngang tiến vào hang cọp bắt cọp con.",
        "A Sửu khẽ vén một góc rèm kiệu nhìn ngắm phố xá tấp nập bên ngoài, tự nhủ với lòng mình nhất định phải sinh tồn và sống sót trở về trong vinh quang rực rỡ nhất."
    ),
    # 33
    (
        1425.00, 1469.53, "suspense",
        "Đoàn rước dâu rầm rộ dần dần tiến về phía cổng phủ Anh Quốc Công uy nghiêm sừng sững, nơi cánh cổng sắt sơn son khổng lồ đang từ từ mở rộng đón đoàn rước dâu vào nội viện.",
        "Bầu không khí ở nơi đây tĩnh mịch và trang nghiêm đến ngột ngạt, tuyệt nhiên không có tiếng cười đùa rộn rã mà chỉ thoang thoảng mùi thuốc bắc nồng nặc bay trong gió lạnh.",
        "Dấu hiệu cảnh báo rõ ràng cho thấy tình trạng nguy kịch thập tử nhất sinh của vị thế tử nằm bên trong quả thực không hề bị phóng đại một chút nào cả."
    ),
    # 34
    (
        1469.53, 1514.06, "serious",
        "Kiệu hoa hạ xuống trước bậc tam cấp thềm rồng lót thảm đỏ, bà mối đỡ lấy tân nương cẩn thận bước qua chậu than hồng rực lửa theo đúng phong tục cổ xưa xua đuổi tà khí xui xẻo.",
        "Từng nghi thức bái đường thành thân được cử hành vô cùng nhanh chóng và gấp gáp dưới sự chứng kiến nghiêm trang của các vị bô lão và quan khách hai họ quyền quý.",
        "Tất cả mọi người có mặt đều nơm nớp lo sợ thế tử chẳng may tắt thở giữa chừng thì đám cưới linh đình này sẽ biến thành đám tang tang tóc ngay trong nháy mắt."
    ),
    # 35
    (
        1514.06, 1558.59, "normal",
        "A Sửu được hai tỳ nữ dìu đưa thẳng vào căn phòng tân hôn u tối và tĩnh lặng, nơi chiếc giường gỗ lim chạm khắc tinh xảo đang buông rèm lụa dày đặc cách biệt thế gian.",
        "Trên chiếc giường hỷ, một chàng trai tuấn tú phi phàm với đường nét gương mặt góc cạnh sắc nét đang nằm bất động, sắc mặt nhợt nhạt không vướng một giọt máu tươi.",
        "Đó chính là Lục Trạc, vị chiến thần trẻ tuổi bách chiến bách thắng lẫy lừng nơi sa trường nay lại phải chịu cảnh nằm liệt một chỗ chờ ngày số mệnh an bài định đoạt."
    ),
    # 36
    (
        1558.59, 1603.12, "suspense",
        "Đám gia nhân và bà mối sau khi hoàn tất các thủ tục giao bôi hình thức liền vội vã cúi đầu lui hết ra ngoài, cẩn thận khóa chặt then cài cửa phòng lại từ bên ngoài.",
        "Căn phòng tân hôn rộng lớn và trang trọng giờ đây chỉ còn lại hai con người hoàn toàn xa lạ, một người hôn mê bất tỉnh nhân sự và một người mang thân phận giả mạo thế thân.",
        "A Sửu tự tay vén chiếc khăn voan đỏ thêu phượng hoàng ra, khẽ thở phào nhẹ nhõm một hơi dài sau chuỗi thời khắc căng thẳng tột độ đến mức nghẹt thở."
    ),
    # 37
    (
        1603.12, 1647.66, "punchline",
        "Nàng tiến lại gần bàn trà, thong thả rót một chén nước lọc rồi bốc ngay một miếng bánh ngọt đưa vào miệng nhai ngon lành để lót dạ sau cả một ngày dài nhịn đói mệt mỏi.",
        "Vừa ăn nàng vừa ngắm nghía vị phu quân trên danh nghĩa của mình, thầm nghĩ bụng chàng thế tử này khôi ngô tuấn tú phong độ thế này mà chết yểu thì quá là phí phạm của trời.",
        "Dù sao thì việc xung hỷ cũng đã hoàn thành êm đẹp, nàng chỉ việc diễn tròn vai một người vợ hiền thảo chăm sóc phu quân để chờ ngày mẹ nuôi bình phục hoàn toàn ở quê."
    ),
    # 38
    (
        1647.66, 1692.19, "excited",
        "Nhưng đúng lúc A Sửu bước lại gần mép giường cúi người định chỉnh lại chăn ấm cho phu quân, một bàn tay lạnh ngắt như băng bất ngờ vươn lên chộp chặt lấy cổ tay nàng.",
        "Lực nắm mạnh mẽ và dứt khoát như một chiếc gọng kìm sắt đá khiến nàng giật thót tim, đánh rơi cả chiếc khăn tay thêu hoa sen quý giá xuống nền đất lạnh.",
        "Đôi mắt sâu thẳm đen nhánh của Lục Trạc khẽ mở ra từ từ, ánh nhìn sắc bén và lạnh lùng như lưỡi gươm báu lập tức chiếu thẳng vào dung mạo của nàng tân nương mới cưới."
    ),
    # 39
    (
        1692.19, 1736.72, "suspense",
        "Vị thế tử tưởng chừng như sắp sửa đi chầu trời nay lại hồi tỉnh một cách thần kỳ đến khó tin ngay trong đêm tân hôn định mệnh đầu tiên của hai người.",
        "Sát khí và khí tức lạnh lẽo bao trùm khắp căn phòng khi chàng cất giọng khàn đặc đầy uy quyền gặng hỏi rằng nàng rốt cuộc là ai và do kẻ nào phái đến đây ám hại chàng.",
        "A Sửu sững sờ trong giây lát ngắn ngủi, nhưng bản năng sinh tồn mãnh liệt của một cô gái từng lăn lộn va vấp chốn giang hồ nghèo khó lập tức phát huy tác dụng kịp thời."
    ),
    # 40
    (
        1736.72, 1781.25, "serious",
        "Nàng không hề luống cuống run rẩy hay để lộ chút hoảng loạn nào, trái lại nhẹ nhàng đỡ chàng ngồi tựa vào thành giường rồi rót ngay một chén trà ấm dâng tới tận miệng chàng.",
        "Nàng từ tốn cất lời giải thích rằng thiếp là thê tử hợp pháp do Thừa An Bá phủ gả sang để hầu hạ chàng, xin thế tử bớt giận giữ gìn sức khỏe đang lúc trọng thương.",
        "Sự bình thản và điềm tĩnh khác thường của nàng thê tử mới cưới khiến vị thế tử đa nghi, sắc sảo bắt đầu dấy lên mối hoài nghi sâu sắc về thân thế thực sự của nàng."
    ),
    # 41
    (
        1781.25, 1825.78, "normal",
        "Lục Trạc uống cạn chén nước ấm dịu giọng, ánh mắt chàng vẫn không rời khỏi từng nét mặt và cử chỉ biểu cảm nhỏ nhất của người con gái đang đứng trước mắt mình.",
        "Chàng tinh ý nhận ra đôi bàn tay của nàng tuy được bôi phấn trắng mịn màng nhưng nơi khớp ngón tay lại có những vết chai sạn đặc trưng của người từng lao động vất vả lâu năm.",
        "Một thiên kim tiểu thư quyền quý sống trong nhung lụa từ tấm bé tuyệt đối không thể nào sở hữu đôi bàn tay chai sần lam lũ của tầng lớp bần hàn như thế này được."
    ),
    # 42
    (
        1825.78, 1870.31, "punchline",
        "A Sửu tinh ý phát hiện ra ánh mắt chàng đang săm soi đôi bàn tay mình, liền nhanh trí giả vờ ngượng ngùng e thẹn giấu vội tay vào trong ống tay áo rộng thùng thình.",
        "Nàng lanh lợi chống chế rằng dạo gần đây nàng thường xuyên ăn chay niệm Phật, chép kinh cầu an cho thế tử nên ngón tay mới bị chai cứng vì cầm bút lông nhiều ngày.",
        "Lý do nghe qua thì vô cùng hợp lý và tràn ngập nghĩa tình phu thê sâu sắc, nhưng trong bụng vị thế tử từng trải thì thừa biết tỏng nàng đang bốc phét không hề chớp mắt."
    ),
    # 43
    (
        1870.31, 1914.84, "suspense",
        "Bên ngoài khung cửa sổ phòng tân hôn, bóng dáng của một tỳ nữ thân tín do thế lực ngầm trong phủ cài cắm đang lén lút dòm ngó nghe ngóng mọi động tĩnh bên trong.",
        "Nhận thấy có kẻ rình rập ngoài hiên, Lục Trạc bất ngờ đưa tay kéo mạnh A Sửu ngã nhào vào lòng mình trên chiếc giường hỷ phủ đầy những cánh hoa hồng thơm ngát.",
        "Hành động táo bạo và quá đỗi đường đột của người phu quân khiến A Sửu đỏ bừng hai gò má, trái tim đập thình thịch liên hồi như tiếng trống trận dồn dập trong lồng ngực."
    ),
    # 44
    (
        1914.84, 1959.38, "excited",
        "Chàng ghé sát làn môi vào tai nàng thì thầm ra lệnh rằng hãy phối hợp diễn một màn kịch ân ái mặn nồng để đánh lạc hướng tai mắt rình mò của kẻ thù xung quanh phủ đệ.",
        "Hiểu được tình thế nguy hiểm ngàn cân treo sợi tóc, A Sửu lập tức bắt nhịp hùa theo, cất lên tiếng nũng nịu ngọt ngào như rót mật vào tai vị thế tử tuấn tú.",
        "Kẻ theo dõi bên ngoài nghe thấy những thanh âm thân mật tình tứ liền tin chắc mọi chuyện êm đẹp, vội vã rút lui trong đêm tối để bẩm báo lại cho kẻ chủ mưu đứng sau giật dây."
    ),
    # 45
    (
        1959.38, 2003.91, "serious",
        "Khi bóng kẻ địch đã hoàn toàn đi xa, hai người lập tức tách nhau ra giữ khoảng cách an toàn, ánh mắt nhìn nhau chứa chan sự đề phòng và những toan tính vô cùng sâu xa.",
        "Một liên minh sinh tồn bất đắc dĩ giữa chàng thế tử trùng sinh phục hồi sức mạnh và nàng thiên kim giả mạo xuất thân từ đáy xã hội chính thức được thiết lập vững chắc.",
        "Cả hai con người này đều mang trong mình những bí mật động trời cần che giấu và cùng đối mặt với những kẻ thù hiểm ác đang rình rập muốn dồn họ vào chỗ chết không toàn thây."
    ),
    # 46
    (
        2003.91, 2048.44, "normal",
        "Cùng thời điểm đó tại Thừa An Bá phủ, Quân Đại sau khi trút bỏ được gánh nặng của cuộc hôn sự xung hỷ quái ác thì đang ung dung ngồi thưởng thức trà thơm bánh ngọt trong phòng.",
        "Ả ta vô cùng đắc ý tự mãn cho rằng nước cờ tráo người của mình quá đỗi hoàn hảo, vừa giữ được thân thể ngọc ngà vừa tống khứ được kẻ có gương mặt giống hệt mình đi xa xứ.",
        "Nhưng người tính chẳng bằng trời tính, ả không thể nào ngờ được rằng việc đẩy A Sửu đi thay mình chính là nhát dao chí mạng tự tay chặt đứt tương lai của chính bản thân."
    ),
    # 47
    (
        2048.44, 2092.97, "suspense",
        "Trong căn phòng thờ gia tộc âm u khói hương nghi ngút, Bá phu nhân quỳ sụp trước bài vị tổ tiên bật khóc nức nở thảm thiết vì nỗi dằn vặt tội lỗi suốt bao nhiêu năm chôn giấu.",
        "Ký ức kinh hoàng của mười sáu năm về trước hiện về như một cuốn phim quay chậm: cảnh tượng tráo đổi hai đứa trẻ sơ sinh trong một đêm mưa gió bão bùng sấm chớp rền vang.",
        "Đứa trẻ mang dòng máu huyết thống chính thống cao quý của Thừa An Bá phủ thực chất lại chính là Ngụy Nhiêu, tức A Sửu cô gái gánh dạ hương nghèo khó ngày hôm nay."
    ),
    # 48
    (
        2092.97, 2137.50, "serious",
        "Còn Quân Đại, đứa con gái được cưng chiều nâng niu như ngọc như ngà suốt bao năm qua thực chất chỉ là đứa con hoang của bà cô bên ngoại tráo vào để nhận vơ danh phận vinh hoa.",
        "Bá phu nhân toàn thân run rẩy sợ hãi một ngày nào đó sự thật bị phơi bày ra ánh sáng công lý, gia tộc sẽ tan nát và bản thân bà sẽ không còn mặt mũi nào xuống suối vàng nhìn tổ tiên.",
        "Bi kịch trớ trêu thay khi chính tay kẻ giả mạo lại tống khứ người thừa kế danh chính ngôn thuận vào thẳng vòng tay quyền lực của vị thế tử hiển hách nhất triều đình."
    ),
    # 49
    (
        2137.50, 2182.03, "punchline",
        "Đúng là người tính không bằng trời tính, tưởng đâu bày mưu tính kế đẩy người ta vào chỗ chết ai ngờ lại vô tình tạo cơ hội cho chim phượng hoàng đích thực tái sinh từ đống tro tàn.",
        "Khán giả theo dõi đến phân đoạn này chỉ biết vỗ đùi đánh đét khen ngợi biên kịch quay xe quá gắt, quả báo đến tuy có phần muộn màng nhưng chắc chắn sẽ đến nơi đến chốn.",
        "Tập đầu tiên đã hoàn thành việc thiết lập bàn cờ nhân vật một cách vô cùng xuất sắc, dọn đường cho những màn cung đấu trả đòn rực lửa gay cấn ở các tập tiếp theo."
    ),
    # 50
    (
        2182.03, 2226.56, "normal",
        "Sáng sớm hôm sau, tin tức chấn động về việc thế tử Anh Quốc Công hồi tỉnh thần kỳ sau đêm tân hôn lập tức lan truyền khắp toàn bộ kinh thành phồn hoa như một cơn lốc xoáy dữ dội.",
        "Từ quan viên cho đến thứ dân ai nấy đều trầm trồ ca tụng nhị tiểu thư Thừa An Bá phủ quả nhiên mang số mệnh đại cát đại lợi, vừa bước chân vào cửa là mang lại sinh khí dồi dào.",
        "Tin lành chấn động bay về Thừa An Bá phủ khiến Quân Đại đang nhâm nhi điểm tâm nghe xong mà sặc trà suýt nghẹn chết vì kinh hoàng bàng hoàng tột độ không dám tin vào tai mình."
    ),
    # 51
    (
        2226.56, 2271.09, "excited",
        "Ả ta bàng hoàng nhận ra mình vừa tự tay dâng tặng vị trí thế tử phi quyền quý và người chồng đẹp trai tài giỏi ngút ngàn cho một con nhỏ gánh dạ hương hèn hạ mà ả khinh bỉ.",
        "Cơn ghen tức điên cuồng và hối hận muộn màng trào dâng trong lòng khiến Quân Đại phát điên, lập tức toan tính những thủ đoạn đê hèn mới để tìm cách lật tẩy và triệt hạ A Sửu.",
        "Từ vị thế của kẻ chủ động ban phát số phận cho người khác, nay ả ta đã biến thành kẻ thua cuộc thảm hại, nơm nớp lo sợ bị lật ngược tình thế và mất trắng mọi thứ trong tay."
    ),
    # 52
    (
        2271.09, 2315.62, "serious",
        "Trong khi đó tại Anh Quốc Công phủ bề thế, A Sửu bắt đầu đón nhận sự kính trọng từ đám gia nhân hầu cận và sự đón tiếp nồng hậu chân tình của các bậc trưởng bối trong phủ.",
        "Nàng tuyệt nhiên không hề tự mãn hay kiêu ngạo vì bước lên mây xanh, trái lại vẫn luôn giữ thái độ khiêm nhường lễ phép, cẩn trọng trong từng lời ăn tiếng nói và cử chỉ thường nhật.",
        "Sự khôn khéo, hiểu chuyện và tinh tế vượt bậc của nàng nhanh chóng chiếm trọn thiện cảm của Lão phu nhân nhà chồng, củng cố vững chắc nền móng địa vị của nàng trong gia tộc quyền uy."
    ),
    # 53
    (
        2315.62, 2360.16, "suspense",
        "Lục Trạc âm thầm quan sát người vợ mới cưới suốt cả ngày trời, càng nhìn chàng càng nhận thấy người con gái này toát lên khí chất bất phàm và bản lĩnh kiên cường hiếm có trong thiên hạ.",
        "Chàng biết chắc chắn thân thế của nàng ẩn chứa uẩn khúc vô cùng lớn, nhưng tạm thời chàng quyết định giữ thái độ im lặng để xem nàng sẽ tiếp tục diễn xuất màn kịch này ra sao.",
        "Mối quan hệ phu thê giữa hai con người tài ba dần chuyển biến từ sự đối đầu nghi ngờ sang sự tôn trọng, đồng cảm và thấu hiểu ngầm sâu sắc qua từng ánh mắt trao nhau."
    ),
    # 54
    (
        2360.16, 2404.69, "normal",
        "Những dòng người tấp nập kéo đến chúc mừng đôi tân lang tân nương mang lại bầu không khí hân hoan rộn ràng khắp phủ đệ sau chuỗi ngày ảm đạm dài dằng dặc vì bệnh tật tang tóc.",
        "Nhạc hỷ rộn rã lại một lần nữa trỗi khúc hoan ca, báo hiệu một chương mới rực rỡ đầy vinh quang sắp sửa mở ra cho số phận của cô gái nghèo từng mang cái tên xấu xí A Sửu.",
        "Từ đáy bùn đen tăm tối của xã hội bước thẳng lên đỉnh cao danh vọng hào môn, hành trình của nàng chỉ mới bắt đầu nhưng đã mang đầy đủ dáng dấp của một thiên truyền kỳ bất hủ."
    ),
    # 55
    (
        2404.69, 2449.22, "punchline",
        "Cái giá của chiếc trâm vàng năm xưa từng là mầm mống cho sự phản bội đê hèn, nay đã được quy đổi bằng cả một cuộc đời mới rực rỡ nơi kẻ ác phải run sợ còn người lương thiện được đền đáp xứng đáng.",
        "Quân Đại đứng từ xa nhìn cỗ xe ngựa quyền quý đi qua trước mắt mà cắn nát cả môi dưới chảy máu, chính thức tuyên chiến trong bóng tối một mất một còn với người chị em sinh đôi.",
        "Cuộc chiến sinh tử giữa hai đóa hoa song sinh cùng chung một gương mặt nhưng khác biệt hoàn toàn về tâm can và cốt cách hứa hẹn sẽ làm nổ tung màn ảnh ở những tập phim gay cấn tiếp theo."
    ),
    # 56
    (
        2449.22, 2493.75, "excited",
        "Tập 1 của Gả Kim Thoa khép lại bằng một phân cảnh tuyệt đẹp khi Lục Trạc mỉm cười dịu dàng đưa bàn tay đỡ lấy A Sửu bước xuống từng bậc thềm trước sự chứng kiến ngưỡng mộ của toàn thể bá quan.",
        "Ánh nắng ban mai rực rỡ ấm áp chiếu rọi lên tà áo đỏ thêu hoa phượng của nàng tân thế tử phi mới, rạng ngời, kiêu hãnh và uy nghi như một bậc mẫu nghi thiên hạ thực thụ.",
        "Một cái kết không thể nào viên mãn và trọn vẹn hơn cho tập phim mở màn, vừa thỏa mãn tâm lý háo hức của người xem vừa gieo rắc vô số sự tò mò chờ đợi cho chặng đường dài phía trước."
    ),
    # 57
    (
        2493.75, 2538.28, "normal",
        "Tiếng hát hào hùng đầy bi tráng và da diết của ca khúc chủ đề mang tên Tá Danh Nhập Cục do nam ca sĩ Lưu Vũ Ninh thể hiện vang lên đưa tập đầu tiên của bộ phim dần đi vào hồi kết.",
        "Từng câu từ lời ca sâu lắng như khắc họa trọn vẹn số phận nghiệt ngã nhưng quật cường của những kiếp người tráo đổi thân phận trong vòng xoáy quyền mưu tranh đoạt ngôi báu.",
        "Một bộ phim cổ trang gia đấu xuất sắc hiếm hoi và chỉn chu bậc nhất của năm nay mà bất kỳ mọt phim chân chính nào cũng tuyệt đối không nên bỏ lỡ dù chỉ một giây phút nào."
    ),
    # 58
    (
        2538.28, 2582.81, "serious",
        "Trước khi bước chân vào phủ Anh Quốc Công, Lục Trạc vốn dĩ đã là vị tướng quân bách chiến bách thắng lừng lẫy sa trường, từng khiến quân địch nghe danh là hồn xiêu phách lạc.",
        "Vết thương trúng tên độc hiểm ác trên chiến trường thực chất là một âm mưu ám hại vô cùng tinh vi và thâm độc xuất phát từ chính những thế lực ngầm trong nội bộ triều đình cài cắm.",
        "Sự hồi tỉnh bất ngờ và ngoạn mục của chàng không chỉ làm đảo lộn hoàn toàn kế hoạch đen tối của kẻ thù mà còn vô tình biến nàng thê tử mới cưới thành mục tiêu bảo vệ hàng đầu của chàng."
    ),
    # 59
    (
        2582.81, 2627.34, "suspense",
        "Ngay trong đêm tân hôn đầu tiên đầy biến động, Lục Trạc đã bí mật ra ám hiệu cho thuộc hạ thân tín trong bóng tối âm thầm điều tra toàn bộ chân tướng và lai lịch của nàng dâu mới.",
        "Chàng nhận thấy từng hành vi cử chỉ của A Sửu tuy rất mực đoan trang lễ giáo nhưng ánh mắt lại luôn toát lên vẻ cảnh giác cao độ và sự nhạy bén của một loài báo săn mồi lão luyện.",
        "Rõ ràng đây không phải là một vị tiểu thư khuê các mềm yếu chỉ biết cầm kỳ thi họa và ru rú trong chốn hậu phòng son rỗi để người khác định đoạt số phận của mình."
    ),
    # 60
    (
        2627.34, 2671.88, "normal",
        "Về phần nàng A Sửu, sáng sớm thức dậy nàng đã chủ động xắn cao tay áo bước vào gian bếp nấu một nồi canh bồi bổ thượng hạng thơm phức cho phu quân đang trong thời gian dưỡng thương phục hồi.",
        "Mùi canh thơm lừng ngào ngạt lan tỏa khắp sân viện khiến đám đầu bếp kỳ cựu gia truyền trong phủ cũng phải tròn xoe đôi mắt thán phục tay nghề nấu nướng điêu luyện tài tình.",
        "Họ đâu biết rằng ở quê nhà lam lũ, tài nấu nướng sinh tồn khéo léo của nàng đã được tôi luyện bền bỉ qua hàng ngàn bữa cơm đạm bạc chắt chiu từng cọng rau để nuôi dưỡng mẹ già ốm yếu."
    ),
    # 61
    (
        2671.88, 2716.41, "punchline",
        "Lục Trạc húp trọn bát canh nóng hổi đậm đà, cảm giác một luồng chân khí ấm áp dễ chịu lan tỏa khắp kinh mạch toàn thân giúp vết thương sâu mau chóng hồi phục lành lặn.",
        "Chàng mỉm cười trêu chọc nàng rằng không ngờ nhị tiểu thư Thừa An Bá phủ danh gia vọng tộc vừa giỏi làm thê tử hiền thục lại vừa có tài nấu nướng siêu hạng như một đầu bếp trứ danh.",
        "A Sửu liếc xéo chàng một cái sắc sảo rồi hóm hỉnh đáp rằng nếu chàng còn dám nghi ngờ lòng dạ chân thành của thiếp thì lần sau canh sẽ được nêm thêm một thìa ớt bột cay xé lưỡi cho chàng nếm thử."
    ),
    # 62
    (
        2716.41, 2760.94, "suspense",
        "Bên ngoài khuôn viên phủ Anh Quốc Công uy nghi, các thế lực thù địch bắt đầu rục rịch chuyển động ngấm ngầm khi đón nhận hung tin vị chiến thần trẻ tuổi đã thần kỳ mở mắt bình phục khỏe mạnh.",
        "Những bức mật thư đen chứa đầy toan tính hiểm độc được bí mật chuyển giao đi trong đêm tối, báo hiệu một cơn bão táp cung đình kinh thiên động địa chuẩn bị đổ ập xuống đầu đôi tân lang tân nương trẻ tuổi.",
        "Một cuộc đấu trí không cân sức nơi hậu viện thâm sâu và chốn triều đình gió tanh mưa máu chính thức kéo cờ khai cuộc với những nước cờ cân não đến nghẹt thở từng phút giây."
    ),
    # 63
    (
        2760.94, 2805.47, "excited",
        "A Sửu đứng lặng lẽ bên khung cửa sổ ngắm nhìn bầu trời kinh thành lộng gió mây ngàn, bàn tay khẽ siết chặt chiếc khăn thêu kỷ vật quý giá mà mẹ nuôi đã trao cho nàng trước ngày lên đường xuất giá.",
        "Nàng tự nhủ với cõi lòng mình rằng dù phong ba bão táp ngoài kia có dữ dội và tàn khốc đến đâu, nàng cũng sẽ kiên cường đứng vững như bàn thạch để bảo vệ gia đình và người thân yêu nhất của mình.",
        "Ánh mắt nàng bừng sáng ngọn lửa quyết tâm rực cháy, sẵn sàng đạp bằng mọi chông gai cạm bẫy hiểm trở để cùng phu quân viết nên thiên huyền thoại hiển hách của riêng mình."
    ),
    # 64
    (
        2805.47, 2850.00, "punchline",
        "Chiếc trâm vàng định mệnh năm nào từng là mồi lửa khởi nguồn cho sự phản bội và tráo đổi số phận, nay lại trở thành chiếc chìa khóa vạn năng mở toang cánh cửa danh vọng rực rỡ cho nàng bước vào hào môn.",
        "Quân Đại ngỡ mình là kẻ giăng bẫy tài ba khôn ngoan nhất thiên hạ, nhưng rốt cuộc ả ta chỉ là một con cờ vô tình dâng tặng cả tương lai xán lạn và giang sơn hiển hách cho người khác hưởng trọn.",
        "Màn kết tập một quá đỗi mãn nhãn và thuyết phục khiến người xem phải trầm trồ vỗ tay tán thưởng không ngớt, vô cùng háo hức chờ đón những màn lật kèo nảy lửa và trừng phạt kẻ ác ở các tập tiếp theo."
    )
]

ASSESSMENT_TEXT = (
    "Tập một Gả Kim Thoa có nhịp phim nhanh gọn, mâu thuẫn thế gả thiết lập sắc nét và diễn xuất phân thân của Điền Hi Vi cực kỳ lôi cuốn. "
    "Màu phim sang trọng cùng âm nhạc hoành tráng tạo cảm giác điện ảnh rõ rệt. "
    "Đây chắc chắn là tác phẩm cổ trang gia đấu đáng xem nhất thời điểm hiện tại cho các mọt phim cung đấu."
)


def generate():
    segments = []
    for seg_id, item in enumerate(ENRICHED_STORY, start=1):
        start, end, emo, text1, text2, text3 = item
        narration = [
            SpeechUnit(id=f"u{seg_id}_1", text=text1, emotion=emo),
            SpeechUnit(id=f"u{seg_id}_2", text=text2, emotion=emo),
            SpeechUnit(id=f"u{seg_id}_3", text=text3, emotion="normal" if emo != "punchline" else "punchline"),
        ]
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

    # Assessment segment
    segments.append(ReviewSegment(
        id=65,
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
    bak_file = ROOT / "input" / "scripts" / "review.ga_kim_thoa_ep01.json.bak"
    if out_file.exists():
        bak_file.write_text(out_file.read_text(encoding="utf-8"), encoding="utf-8")

    out_file.write_text(script.model_dump_json(indent=2), encoding="utf-8")

    # Validate
    loaded = ReviewScript.load(out_file)
    story_words = sum(sum(len(u.text.split()) for u in s.narration) for s in loaded.segments[:-1])
    assessment_words = len(loaded.segments[-1].narration.split())
    total_words = story_words + assessment_words
    expected_duration = total_words / 5.2441
    ratio = expected_duration / 2912.152517
    print(f"Generated {len(loaded.segments)} segments.")
    print(f"Story words: {story_words}, Assessment words: {assessment_words}, Total: {total_words}")
    print(f"Expected duration: {expected_duration:.2f}s ({ratio:.2%} of source)")
    print(f"Editorial range: [1164.86s, 1456.08s] -> {'PASS' if 1164.86 <= expected_duration <= 1456.08 else 'FAIL'}")


if __name__ == "__main__":
    generate()

