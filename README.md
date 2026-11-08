# Review Harness (Linux)

Biến một tập phim thành video review tiếng Việt có lời đọc: agent xem phim và viết kịch bản, máy đọc
bằng ZeroTTS offline, FFmpeg dựng hình theo từng câu đọc. Có dashboard trên trình duyệt để theo dõi
từng bước, duyệt kết quả, chạy và dừng.

```
1 Probe      ffprobe video nguồn, tính ngân sách review 40-50% thời lượng
2 READ       agent xem phim (agy xem proxy video) -> 02_read/timeline.md           [bạn duyệt]
3 WRITE      agent viết kịch bản theo timeline     -> 03_write/review.json          [bạn duyệt]
4 MEASURE    ZeroTTS đọc thật từng segment; lệch 40-50% hoặc đánh giá cuối 10-20 s thì gửi WRITE tự sửa
5 RENDER     cắt shot theo từng câu đọc, viền đen + watermark, trộn giọng với âm gốc, ghép
6 QC         kiểm tra thời lượng/codec, giải mã toàn bộ -> jobs/<job>/final_review.mp4
```

Bản Windows cũ (`review_firm_china/`, `dashboard/`) vẫn nằm nguyên ở nhánh `main`.

## Cài đặt (một lần, không cần sudo)

```bash
git clone https://github.com/TranNguyenAnhKhoa/review_firm_harness.git
cd review_firm_harness && git checkout linux-rebuild
./setup.sh
```

`setup.sh` làm 4 việc:

1. Tìm Python 3.10-3.13 và FFmpeg có libx264 + libass. Máy thiếu thì tạo môi trường riêng
   `.tools/conda` (dùng mamba/conda có sẵn, không có thì tự tải micromamba).
2. Tạo `.venv` và cài gói theo `requirements.txt` (phiên bản ghim cứng).
3. Tải model ZeroTTS (khoảng 870 MB) vào `models/zerotts/ZeroTTS-c2bfbd67`. Sau đó đọc offline.
4. Chạy `./run.sh doctor` để báo còn thiếu gì.

Agent: đăng nhập `agy` (Antigravity CLI) một lần trên máy chạy harness. READ và WRITE mặc định dùng agy.
Muốn dùng `claude` hoặc `codex` cho một bước thì đổi trong dashboard (bước READ/WRITE, mục "Agent cho
bước này") và đăng nhập CLI đó.

## Dùng

```bash
./start.sh                              # dashboard http://127.0.0.1:8790 (Ctrl+C để tắt)
./service.sh install                    # hoặc chạy nền, sống qua logout (systemd --user hoặc nohup)
```

Trên dashboard: bấm **+ Job mới**, chọn video (hoặc gõ đường dẫn), bấm **Tạo job**. Harness chạy Probe +
READ rồi dừng ở cổng duyệt READ. Mở `timeline.md`, đọc, bấm **Duyệt & chạy tiếp** (hoặc **Từ chối** kèm lý
do: lần chạy sau agent đọc lý do đó và làm lại). Tương tự ở WRITE. Sau đó MEASURE, RENDER, QC tự chạy;
video cuối hiện ở bước QC và tab Job.

Máy chạy harness là server từ xa thì mở tunnel từ máy của bạn:

```bash
ssh -L 8790:127.0.0.1:8790 <may-chay-harness>    # rồi mở http://127.0.0.1:8790
```

Dòng lệnh làm được mọi việc như dashboard:

```bash
./run.sh new tap-01 /data/phim/tap01.mp4 --title "Tên phim - Tập 1"
./run.sh run tap-01                     # chạy tới cổng duyệt kế tiếp (bỏ qua bước đã xong)
./run.sh status tap-01
./run.sh approve tap-01 read            # hoặc: ./run.sh reject tap-01 read --note "thiếu đoạn 20:00-25:00"
./run.sh run tap-01 --only measure      # chạy riêng một bước
./run.sh run tap-01 --from write --force   # chạy lại từ WRITE, gọi agent lại
./run.sh check tap-01                   # kiểm tra review.json, ước tính thời lượng đọc
./run.sh import tap-01 timeline file.md # nhập tay khi READ/WRITE để engine manual
./run.sh brief /data/phim/tap01.mp4     # ngân sách thời lượng của một video
./run.sh voice --text "Câu thử giọng." --voice giahuy --out /tmp/thu.wav
```

## Dashboard

- **Danh sách job**: thẻ từng job với thanh tiến độ 6 bước, trạng thái (đang chạy / chờ duyệt / lỗi / xong).
- **Pipeline**: mỗi bước là một ô có trạng thái, engine (agy / claude / codex / zerotts / ffmpeg), số liệu
  chính (độ phủ timeline, ước tính và số đo thời lượng, tiến độ TTS/dựng), thời gian và token của agent.
  Bước nào có đầu vào đổi sau lần chạy trước được đánh dấu "cần chạy lại".
- **Chi tiết**: lỗi, cảnh báo, file kết quả (xem Markdown/JSON, ảnh sheet, proxy video, audio từng segment),
  cổng duyệt, ô dán kết quả tay, đổi agent/model cho READ và WRITE.
- **Log**: log trực tiếp của run đang chạy và các run trước; nút Dừng (dừng cả agent và FFmpeg).
- **Job**: video nguồn, cài đặt (giọng, watermark, âm nền, cổng duyệt, số vòng tự sửa), lịch sử, lưu trữ job.
- **Hệ thống**: kiểm tra môi trường như `./run.sh doctor`.

Giao diện mở ở chế độ sáng, nút **Tối** để đổi. File HTML thuần ASCII nên đọc đúng cả khi trình duyệt
đoán sai bảng mã.

An toàn: dashboard chỉ nghe ở 127.0.0.1. Nó từ chối Host lạ (chống DNS rebinding), chỉ nhận lệnh ghi
từ chính trang của nó (header `X-Harness` + kiểm tra Origin), không gửi header CORS, chỉ phục vụ file
nằm trong thư mục job, và chỉ khởi chạy đúng lệnh `python -m harness run` với tham số đã kiểm tra.
Dashboard không có đăng nhập: đừng mở ra mạng (`HARNESS_HOST=0.0.0.0`) nếu người khác vào được cổng đó.

## Agent làm gì, thấy gì

| Bước | agy (mặc định) | claude / codex |
| --- | --- | --- |
| READ | Xem proxy 360p, mỗi đoạn 10 phút, có timecode nguồn in ở góc trái trên | Xem sheet khung hình (4x4, có giờ), sheet dải phụ đề cứng, transcript Whisper nếu bật |
| WRITE | Đọc timeline đã duyệt, quy tắc biên tập, mẫu JSON, danh sách cắt cảnh | Như agy; claude còn tự chạy `./run.sh check` |

Agent chạy từ thư mục harness (đọc `AGENTS.md`), chỉ được ghi đúng một file trong thư mục job. agy
không được chạy lệnh shell (chế độ headless từ chối và dừng phiên), nên prompt chỉ cho phép tool đọc/ghi
file. claude chỉ được 2 lệnh shell: `./run.sh frame` (lấy khung hình đầy đủ ở một giây bất kỳ) và
`./run.sh check`. Kết quả READ/WRITE được kiểm tra tự động (front matter, bảng timeline có start/end,
schema review, cấu trúc assessment); sai thì agent được yêu cầu sửa, tối đa `agents.write.fix_rounds` lần.

## Thư mục

```
config/default.yaml   mọi cài đặt; job ghi đè trong jobs/<job>/config.yaml
prompts/              prompt READ và WRITE (có chỗ điền {{...}})
docs/                 quy tắc biên tập, giọng đọc, mẫu 1004
harness/              package Python: pipeline/ (job, stages, runner, agents), audio/, video/, monitor/ (dashboard)
jobs/<job>/           job.json, config.yaml, state.json, events.jsonl, runs/*.log,
                      01_probe ... 06_qc, final_review.mp4
media/                chỗ đặt video nguồn (không vào git)
models/ .tools/ .venv/   do setup.sh tạo (không vào git)
tests/                61 test: chạy .venv/bin/python -m unittest discover -s tests
```

Đường dẫn video nằm trong `media/` được lưu tương đối, nên chép cả thư mục harness sang máy khác vẫn chạy.

## Job chuyển từ bản Windows

`jobs/ga_kim_thoa_ep01` giữ timeline (Antigravity Desktop) và review.json 65 segment của bản cũ, đang chờ
duyệt READ. Để chạy tiếp: chép video vào `media/ga_kim_thoa_ep01.mp4`, chạy bước Probe, rồi duyệt READ và
WRITE (hoặc chạy lại READ bằng agy: timeline cũ chỉ có 10 dòng cho 48 phút và không có bảng shot).

## Lưu ý

- `render.picture_style.fit_mode: cover` (mặc định, theo mẫu 1004) cắt bớt trên/dưới khung nguồn, có thể
  mất một phần phụ đề cứng sát đáy. `contain` giữ nguyên khung.
- Số giây do TTS đo và file đã dựng là căn cứ cuối. Không đệm im lặng hay đọc chậm để đủ tỷ lệ.
- Nội dung (câu đùa, nhận xét) vẫn cần người xem lại: code chỉ kiểm tra cấu trúc và thời lượng.
- Sửa giao diện: sửa `harness/monitor/static/index.src.html`, rồi chạy
  `.venv/bin/python -m harness.monitor.asciify` để tạo lại `index.html` thuần ASCII.
