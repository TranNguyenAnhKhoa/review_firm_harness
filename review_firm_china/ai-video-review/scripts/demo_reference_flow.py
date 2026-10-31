"""Build a standalone technical demo with the default reference flow and real Bao Trang."""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.pipeline.build_review import build_review
from src.utils import executable, run_command


def main():
    output = ROOT/'output/reference1004_demo'
    output.mkdir(parents=True,exist_ok=True)
    video = output/'source.mp4'
    if not video.exists():
        run_command([executable('ffmpeg','FFMPEG_BINARY'),'-v','error','-y',
                     '-f','lavfi','-i','testsrc2=size=640x360:rate=30:duration=60',
                     '-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p',str(video)])
    # Only a technical test pattern is described; this is not a film plot or film review.
    story = ('Vừa bật video, cả bảng màu đã chen nhau lên hình như đang tranh vai chính. '
             'Cảnh tiếp theo xuất hiện ngay khi câu kể chuyển ý, rồi lại cắt sang một góc nhìn khác. '
             'Bảo Trang dẫn câu chuyện liên tục, còn hình ảnh thay đổi để người xem không phải nhìn một cảnh quá lâu. '
             'Mỗi nhịp cắt đều theo lời đọc đã đo, thay vì kéo hình đứng yên cho đủ thời lượng.')
    assessment = ('Điểm rõ nhất của bản thử là lời đọc liền mạch và nhịp cắt gọn, '
                  'hình ảnh cũng có khung ngang cùng tên kênh nhỏ ở góc. '
                  'Tuy vậy, bảng màu chỉ chứng minh phần kỹ thuật, chưa cho biết cách kể một bộ phim có cuốn hay không. '
                  'Khi dùng phim thật, cần chọn đúng hành động và phản ứng nhân vật, rồi nghe xem lại toàn bộ trước khi xuất bản.')
    data = {'title':'Demo kỹ thuật flow theo mẫu 1004, giọng Bảo Trang','source_video':str(video),
            'segments':[{'id':1,'section':'story','narration':story,'source_start':0,'source_end':40,
                         'keep_original_audio':False,
                         'shots':[{'source_start':i*4,'source_end':i*4+4} for i in range(10)]},
                        {'id':2,'section':'assessment','narration':assessment,'source_start':40,'source_end':60,
                         'keep_original_audio':False,
                         'shots':[{'source_start':40+i*2,'source_end':44+i*2} for i in range(9)]}]}
    script = output/'review.json'
    script.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    config = output/'demo.yaml'
    # Match the reference layout; use a faster encoding preset only for this technical demo.
    config.write_text('video:\n  preset: veryfast\n',encoding='utf-8')
    final = build_review(str(video),str(script),str(config),output_dir=str(output/'artifacts'))
    run_command([executable('ffmpeg','FFMPEG_BINARY'),'-v','error','-xerror','-i',str(final),
                 '-map','0:v:0','-map','0:a:0','-f','null','-'])
    frame = output/'preview.png'
    run_command([executable('ffmpeg','FFMPEG_BINARY'),'-v','error','-y','-ss','3','-i',str(final),
                 '-frames:v','1',str(frame)])
    print(f'Full decode PASS: {final}',flush=True)


if __name__ == '__main__':
    main()
