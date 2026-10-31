"""Apply picture-sampled editorial corrections to a NEW revision (never to the original)."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.pipeline.schema import ReviewScript
from src.audio.narration_segmenter import NarrationSegmenter
from src.audio.emotion_planner import HeuristicEmotionPlanner
from scripts.revise_moana import split_balanced

RANGES={6:(1330,1890),7:(1890,2090),8:(2090,2220),9:(2220,2520),
    11:(2850,3100),12:(3100,3330),13:(3330,3650),14:(3650,3920),15:(3920,4160),
    16:(4160,4240),18:(4240,4520),17:(4520,4805),19:(4805,4900),20:(4900,5140),
    21:(5140,5380),22:(5380,5640),23:(5640,5730),24:(5730,5900),25:(5900,6140),
    26:(6140,6280),27:(6280,6325),28:(6285,6320)}

REWRITES={
8: '''Mang theo lời nhờ cậy của bà, Moana chuẩn bị rời nhà trong tâm trạng vừa lo lắng vừa quyết tâm. Cô biết phía trước là một hành trình chưa từng trải qua, còn phía sau là những người thân mình không muốn mất. Lúc Sina xuất hiện, Moana lo mẹ sẽ ngăn lại. Nhưng người mẹ lặng lẽ giúp con chuẩn bị. Không cần một lời tuyên bố dài, sự chăm sóc ấy cho thấy bà hiểu lựa chọn khó khăn của con gái. Được tiếp thêm sức mạnh, Moana đưa thuyền ra biển trong đêm. Con thuyền nhỏ phải vượt qua rạn san hô từng khiến cô thất bại. Lần này, chuyến đi không chỉ xuất phát từ sự tò mò; cô đang mang theo hy vọng cứu lấy quê hương. Hình ảnh cá đuối phát sáng gắn với bà Tala xuất hiện bên hành trình của Moana. Giữa nỗi buồn chia xa, cô vẫn cảm nhận được sự đồng hành của người bà. Biển đêm vừa rộng lớn vừa xa lạ, nhưng Moana đã lựa chọn bước tiếp. Cô giương buồm hướng ra khơi, bắt đầu cuộc tìm kiếm Maui và con đường hoàn trả trái tim.''',
16: '''Moana nhận ra sức mạnh không thể giúp họ thắng Tamatoa lúc này. Cô tận dụng thứ phát sáng để đánh lạc hướng con cua đang mê mẩn đồ lấp lánh. Mục tiêu là khiến hắn rời sự chú ý khỏi Maui. Trò đánh lừa tạo ra một cơ hội ngắn, và cả hai phải hành động ngay. Khi Tamatoa nhận ra sự thật, Moana và Maui đã tìm đường thoát. Dòng nước phun trào giúp họ rời khỏi nơi nguy hiểm và trở lại bên ngoài. Chiếc lưỡi câu đã lấy được, nhưng Maui chưa thể xem như mọi vấn đề đều giải quyết xong. Còn Moana vừa cho thấy sự quan sát và nhanh trí của mình có thể giúp cả đội trong tình thế mà sức mạnh của á thần không đủ.''',
18: '''Trở lại sau cuộc chạm trán Tamatoa, Maui phải đối diện một điều khó chịu: lấy được lưỡi câu không có nghĩa là lập tức làm chủ được nó. Anh tiếp tục thử sử dụng phép biến hình, trong khi Moana phải học thêm cách xử lý những tình huống trên biển. Họ chưa phải một đội hoàn hảo. Một người có nhiều kinh nghiệm nhưng mang theo niềm kiêu hãnh, người kia kiên trì nhưng vẫn còn những điều chưa biết. Trên chuyến đi, việc thực hành và quan sát quan trọng không kém lời chỉ dẫn. Con thuyền trở thành nơi cả hai phải học cách phối hợp, thay vì chỉ tranh luận xem ai đúng. Sự tự tin của Maui cũng chưa trở lại trọn vẹn. Chính khoảng cách giữa hình ảnh á thần anh muốn giữ và điều anh đang cảm thấy dẫn tới cuộc trò chuyện sâu hơn về quá khứ của mình.''',
19: '''Te Kā xuất hiện giữa khói lửa, biến những lời cảnh báo thành nguy hiểm ngay trước mắt. Maui đối đầu với quái vật, còn Moana tìm cách đưa thuyền tiến lên. Nhưng sức mạnh trước mặt vượt xa một thử thách thông thường. Maui yêu cầu quay lại, trong khi Moana vẫn muốn tìm đường vượt qua. Sự khác biệt trong quyết định khiến họ mất nhịp phối hợp. Khi đòn tấn công ập tới, Maui dùng lưỡi câu che chắn. Cả hai bị đánh bật khỏi khu vực giao chiến. Họ còn sống, nhưng chiếc lưỡi câu đã hư hại. Thất bại này không chỉ ngăn con thuyền tới đích; nó còn đe dọa sự tin tưởng vừa được xây dựng giữa hai người.''',
23: '''Khi tiếp cận nơi cần hoàn trả trái tim, Moana nhận ra có điều không đúng với điều mình chờ đợi. Cô không tìm thấy Te Fiti như hình dung. Giữa tình thế nguy hiểm, ánh nhìn của cô hướng tới dấu xoắn trên ngực Te Kā. Những điều tưởng rời rạc bắt đầu nối lại: trái tim bị lấy đi, sự sống mất cân bằng, và một thực thể giận dữ chắn đường. Moana hiểu rằng Te Kā chính là Te Fiti trong trạng thái bị tổn thương. Nhận ra điều ấy, cô thay đổi cách đối mặt. Điều cần làm không còn là tìm cách tiêu diệt một con quái vật. Cô phải đưa trái tim về đúng nơi, và tìm cách tiếp cận người đang đau đớn thay vì chỉ đáp trả sự phẫn nộ.''',
26: '''Moana trở về Motunui, mang theo kinh nghiệm của chuyến đi và niềm vui khi quê hương được hồi sinh. Cha mẹ và dân làng đón cô, khiến hành trình lớn lao trở về với điều rất gần gũi: được gặp lại những người mình yêu thương. Cuộc đoàn tụ không xóa đi những bất đồng từng có, nhưng cho thấy Moana đã đi xa hơn hình ảnh cô gái còn lúng túng trước trách nhiệm. Trong khung cảnh cộng đồng cùng hiện diện, cô bước vào vai trò mới của mình. Không chỉ biết hướng ra biển, cô còn có thể đưa những điều đã học trở lại với người dân. Việc đi xa vì thế không tách cô khỏi cội nguồn. Nó giúp cô hiểu rõ hơn mình muốn dẫn dắt cộng đồng theo hướng nào, và vì sao truyền thống hải hành có thể trở thành một phần tương lai của Motunui.''',
27: '''Những con thuyền Motunui lại hướng ra đại dương. Moana đứng cùng mọi người trong một hành trình không còn chỉ thuộc về riêng cô. Từ chỗ bị ngăn bước qua rạn san hô, cô đã trở thành người có thể góp phần đưa cộng đồng đi tiếp. Điều được mang về không chỉ là sự bình yên cho hòn đảo, mà còn là khả năng nhìn biển bằng một cách khác. Chuyến phiêu lưu khép lại, còn chân trời phía trước vẫn mở ra cho những người vừa tìm lại mối liên hệ với truyền thống hải hành của mình.'''
}
SHORT_EXTRA={
16:[('suspense','Điều cô tận dụng là sự ham muốn của đối thủ, không phải một quyền năng mới.'),
    ('punchline','Tamatoa mê đồ sáng đến mức tự làm khó mình. Vẻ ngoài hấp dẫn chưa chắc đi cùng giá trị thật.'),
    ('excited','Cơ hội chỉ có trong chốc lát. Cả hai cần phối hợp để thoát trước khi đối phương kịp phản ứng.'),
    ('normal','Maui có lưỡi câu, còn Moana có sự nhanh trí. Mỗi người đã góp một phần khác nhau vào cuộc thoát hiểm.')],
19:[('suspense','Biết đối thủ nguy hiểm và thực sự đứng trước nó là hai trải nghiệm rất khác nhau.'),
    ('serious','Can đảm không thay thế được việc phối hợp. Hai người cần một hướng xử lý chung.'),
    ('serious','Ý định cứu quê hương không xóa đi hậu quả của một lựa chọn nóng vội.'),
    ('calm','Vết nứt trên vũ khí cũng chạm vào nỗi sợ sâu kín của Maui.')]
}

def main():
    destination=ROOT/'input/scripts/review.moana.v3.json'
    if destination.exists(): raise FileExistsError(destination)
    review=ReviewScript.load(ROOT/'input/scripts/review.moana.v2.json')
    audit=json.loads((ROOT/'data/timeline/moana/review_v2_editorial.json').read_text(encoding='utf-8'))
    parent={row['segment_id']:row['original_segment_id'] for row in audit['segments']}
    extras={};current=None
    for line in (ROOT/'input/scripts/moana.editorial-additions.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('## '): current=int(line[3:]);extras[current]=[]
        elif ' | ' in line: extras[current].append(line.split(' | ',1))
    segmenter=NarrationSegmenter();planner=HeuristicEmotionPlanner()
    groups={}
    for s in review.segments: groups.setdefault(parent[s.id],[]).append(s)
    for old_id, group in groups.items():
        if old_id in REWRITES:
            units=planner.plan(segmenter.segment(REWRITES[old_id]))
            chunks=split_balanced(units,len(group))
            for index,(s,chunk) in enumerate(zip(group,chunks)):
                narration=[{'text':u.text,'emotion':u.emotion} for u in chunk]
                additions=SHORT_EXTRA.get(old_id,extras.get(old_id,[]))
                if additions:
                    emotion,body=additions[index]
                    if old_id==18:
                        body=body.replace('Một cuộc nói chuyện có thể giúp Maui muốn thử lại, nhưng khả năng vẫn phải trở về qua hành động.',
                                          'Maui muốn lấy lại khả năng của mình, nhưng điều ấy vẫn phải trở về qua hành động.')
                    if old_id==26 and index==1:
                        body='Moana đem điều học được trở lại với cộng đồng. Thay đổi không nhất thiết là phủ nhận nguồn gốc; ở đây, nó mở ra khả năng tiếp nối truyền thống hải hành theo cách chủ động hơn.'
                    narration.extend({'text':u.text,'emotion':emotion} for u in segmenter.segment(body))
                s.narration=ReviewScript.model_validate({'title':'check','segments':[{
                    **s.model_dump(),'narration':narration}]}).segments[0].narration
        a,b=RANGES.get(old_id,(group[0].source_start,group[-1].source_end))
        weights=[len(s.narration_text.split()) for s in group]
        cursor=a
        for index,s in enumerate(group):
            end=b if index==len(group)-1 else round(cursor+(b-a)*weights[index]/sum(weights),3)
            s.source_start,s.source_end=round(cursor,3),end
            s.visual_intent=(f'Moana, nhịp {index+1}/{len(group)} của chương nguồn {old_id}. '
                'Khoảng chương đã đối chiếu ảnh mẫu; ranh giới nhịp là ước lượng biên tập, cần duyệt trước render.')
            cursor=end
    # Pictures show practice before the intimate conversation about Maui's past.
    order=list(range(1,17))+[18,17]+list(range(19,29))
    review.segments=[s for old in order for s in groups[old]]
    review.title='Hành trình của Moana — bản v3 đối chiếu hình mẫu'
    ReviewScript.model_validate(review.model_dump())
    destination.write_text(review.model_dump_json(indent=2,exclude_none=True),encoding='utf-8')
    (ROOT/'data/timeline/moana/review_v3_editorial.json').write_text(json.dumps({
        'analysis_status':'partial','render_ready':False,
        'picture_checks':'99 midpoint frames + 121 refinement frames; not continuous video/audio verification',
        'changes':'Credits excluded; cave/departure/escape/climax/end ranges corrected; practice moved before backstory; unsupported shell ceremony detail removed.',
        'segments':[{'id':s.id,'original_segment_id':parent[s.id],'start':s.source_start,'end':s.source_end,
                     'timestamp_status':'sample_corrected_parent_provisional_subrange'} for s in review.segments]
    },indent=2,ensure_ascii=False),encoding='utf-8')
    print(destination,'segments',len(review.segments),'tokens',sum(len(s.narration_text.split()) for s in review.segments))

if __name__=='__main__':main()
