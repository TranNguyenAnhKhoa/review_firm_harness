"""Compile the curated Moana revision without changing its original review.

Subranges are provisional editorial subdivisions, NOT newly verified scene boundaries.
The sidecar records this limitation; check pictures before rendering.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audio.narration_segmenter import NarrationSegmenter
from src.audio.emotion_planner import HeuristicEmotionPlanner
from src.pipeline.schema import ReviewScript


# Remove unsupported precision, invented causation and exaggerated literal detail.
REPLACEMENTS = {
    'viên ngọc ngọc bích': 'viên ngọc bích',
    'một cô bé bốn tuổi': 'một cô bé',
    'phân phối nguồn nước ngọt cho từng hộ dân, ': '',
    'nồng nặc mùi tử khí': '',
    'đập bàn quát mắng con gái gay gắt': 'phản đối con gái gay gắt',
    'giữ chân mọi người an toàn sau rạn san hô là cách duy nhất để bảo toàn nòi giống': 'giữ mọi người ở phía trong rạn san hô là cách bảo vệ cộng đồng',
    'Những con sóng thần khổng lồ': 'Những con sóng lớn',
    'sắc nhọn. Bàn chân bị đá ngầm cào rách tơi bời': 'sắc nhọn. Bàn chân bị thương',
    'hàng trăm ngọn đuốc cổ xưa đồng loạt bùng cháy rực rỡ': 'không gian hang dần hiện rõ',
    'vĩ đại nhất trong lịch sử nhân loại': 'từng vượt biển khám phá những vùng đất mới',
    'Ông giật lấy ngọn đuốc, kéo Moana xềnh xệch ra bờ biển và tuyên bố sẽ thiêu rụi toàn bộ số thuyền cổ để dập tắt vĩnh viễn ý nghĩ điên rồ này.': 'Ông phản đối việc ra khơi và muốn phá bỏ những chiếc thuyền cổ.',
    'đơn độc độc hành': 'đơn độc',
    'liên tục đòi nhảy xuống biển tự tử': 'liên tục khiến Moana phải giữ cho khỏi rơi xuống biển',
    'nặng cả chục tấn': 'lớn',
    'thì các vị thần': 'thì các vị thần',
    'Maui bẻ lái con thuyền lướt qua một khe hẹp giữa hai chiến hạm, khiến hai cỗ xe tăng nổi của địch đâm sầm vào nhau nổ tung tóe trong làn khói mù mịt.': 'Maui điều khiển thuyền để cả hai thoát khỏi cuộc truy đuổi.',
    'dùng mũi ngửi hướng gió': 'quan sát hướng gió',
    'chưa đầy ba giây sau': 'sau đó',
    'thằn lằn cụt đuôi': 'những hình dạng không như ý',
    'Moana đã dùng mái chèo đập vỡ lớp đá mỏng, kích hoạt một cột nước địa nhiệt phun trào với áp lực kinh hoàng': 'hai người đã tìm được cơ hội thoát ra nhờ dòng nước phun trào',
    'đẩy vọt chiếc thuyền và hai người': 'đẩy hai người',
    'cha mẹ vì thấy đứa con yếu ớt nên đã nhẫn tâm quẳng anh xuống biển sâu để mặc số phận định đoạt': 'cha mẹ đã bỏ anh xuống biển',
    'Các vị thần trao cho anh quyền năng không phải vì anh xứng đáng được yêu thương, mà vì họ thấy được sự vĩ đại bên trong con người anh.': 'Giá trị của Maui không chỉ nằm trong quyền năng của chiếc lưỡi câu.',
    'dự đoán giông bão trước hàng giờ đồng hồ': 'nhận biết điều kiện đi biển',
    'với đôi mắt rực lửa giận dữ ngút trời': 'với ánh mắt dữ dội',
    'trong không khí bỗng đặc quánh mùi lưu huỳnh': 'trong không khí phủ khói',
    'không khí bỗng đặc quánh mùi lưu huỳnh và tro tàn khét lẹt': 'khói và tro phủ kín trước mắt',
    'của một kẻ phàm trần chưa từng biết đến chiến tranh': '',
    'cô gái mười sáu tuổi': 'cô gái trẻ',
    'tình mẫu tử thiêng liêng': 'tình yêu thương dành cho cháu',
    'một vòng chữ S': 'đường vòng',
    'hàng triệu mảnh vụn': 'những mảnh vỡ',
    'sắc bén và quyền năng gấp bội lần xưa': 'để thay cho chiếc đã vỡ',
    'vỗ cánh lượn ba vòng trên bầu trời': 'bay lên bầu trời',
    'Maui trêu đùa rằng cô gái nhỏ giờ đây đã là một Wayfinder thực thụ tài ba hơn cả á thần, rồi anh': 'Maui chia tay người bạn đồng hành, rồi anh',
}


def split_balanced(units, count):
    """Keep speech clauses intact; distribute original narration across ordered beats."""
    groups, cursor = [], 0
    remaining_tokens = sum(len(u.text.split()) for u in units)
    for slot in range(count):
        if slot == count-1:
            groups.append(units[cursor:])
            break
        target = remaining_tokens / (count-slot)
        group, used = [], 0
        while cursor < len(units)-(count-slot-1):
            group.append(units[cursor])
            used += len(units[cursor].text.split())
            cursor += 1
            if used >= target:
                break
        remaining_tokens -= used
        groups.append(group)
    return groups


def main():
    source = ROOT/'input/scripts/review.moana.json'
    output = ROOT/'input/scripts/review.moana.v2.json'
    if output.exists():
        raise FileExistsError('Revision already exists; edit it explicitly instead of overwriting.')
    original = ReviewScript.load(source)
    additions = {}
    for line in (ROOT/'input/scripts/moana.editorial-additions.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            current = int(line[3:])
            additions[current] = []
        elif ' | ' in line:
            additions[current].append(line.split(' | ', 1))
    segmenter, planner = NarrationSegmenter(), HeuristicEmotionPlanner()
    segments, notes = [], []
    soft_sections = {2, 5, 6, 7, 8, 17, 20, 21, 24, 25, 26, 27}
    for old in original.segments:
        text = old.narration_text
        for before, after in REPLACEMENTS.items():
            text = text.replace(before, after)
        if old.id == 1:
            text = text[text.index('Thế nhưng, vừa dứt'):].replace('Thế nhưng, vừa dứt điệu nhạc quen thuộc, ', '', 1)
            text = 'Một cô gái lên đường cứu quê hương, còn người cô cần nhờ giúp lại là á thần từng gây ra rắc rối. Đi tìm đồng đội hay đi đòi người gây chuyện chịu trách nhiệm? Câu chuyện của Moana bắt đầu từ một món nợ như thế. ' + text[0].upper() + text[1:]
        if old.section == 'assessment':
            # Personal assessment, not an unverified claim about release/cast/remake fidelity.
            text = 'Điểm cuốn của Moana, với tôi, là hành trình học cách hiểu người khác thay vì chỉ tìm cách đánh bại họ. Cặp bạn đồng hành trái tính tạo tiếng cười, còn tình thân giữ câu chuyện ấm áp. Ai thích phiêu lưu gắn với trưởng thành sẽ dễ đồng cảm.'
        raw = planner.plan(segmenter.segment(text), section=old.section)
        for i,u in enumerate(raw):
            if old.id in soft_sections and u.emotion == 'normal' and i % 4 == 0:
                u.emotion = 'calm'
        extra = additions.get(old.id, [])
        count = len(extra) or 1
        groups = split_balanced(raw, count)
        start = max(old.source_start, 45) if old.id == 1 else old.source_start
        for index,group in enumerate(groups):
            units = [{'text': u.text, 'emotion': u.emotion} for u in group]
            if extra:
                emotion, content = extra[index]
                units.extend({'text': u.text, 'emotion': emotion} for u in segmenter.segment(content))
            new_id = len(segments)+1
            a = round(start+(old.source_end-start)*index/count, 3)
            b = round(start+(old.source_end-start)*(index+1)/count, 3)
            segments.append({'id': new_id, 'section': old.section, 'source_start': a, 'source_end': b,
                'narration': units, 'visual_intent': old.visual_intent + f' [Nhịp {index+1}/{count}; mốc chia tạm, cần duyệt hình.]',
                'keep_original_audio': old.keep_original_audio})
            notes.append({'segment_id': new_id, 'original_segment_id': old.id, 'source_start': a, 'source_end': b,
                          'timestamp_status': 'provisional_subdivision_not_frame_verified'})
    compiled = ReviewScript.model_validate({'title': original.title+' — bản biên tập v2',
                                           'source_video': original.source_video, 'segments': segments})
    output.write_text(compiled.model_dump_json(indent=2, exclude_none=True), encoding='utf-8')
    audit = ROOT/'data/timeline/moana/review_v2_editorial.json'
    audit.write_text(json.dumps({'source_review_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'timeline_status': 'partial', 'render_ready': False,
        'notes': 'Added interpretive commentary, not newly observed plot. Verify source subranges before rendering.',
        'segments': notes}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)
    print('Segments:',len(segments),'tokens:',sum(len(s.narration_text.split()) for s in compiled.segments))


if __name__ == '__main__':
    main()
