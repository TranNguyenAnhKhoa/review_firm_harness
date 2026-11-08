# Review Harness (Linux)

Biến một tập phim thành video review tiếng Việt có lời đọc. Agent xem phim và viết kịch bản, ZeroTTS đọc
offline, FFmpeg cắt hình theo từng câu đọc. Dashboard trên trình duyệt cho xem từng bước, duyệt kết quả,
chạy và dừng.

```
1 Probe      ffprobe video nguồn, tính ngân sách review 40-50% thời lượng
2 READ       agent xem phim (agy xem proxy video) -> 02_read/timeline.md           [bạn duyệt]
3 WRITE      agent viết kịch bản theo timeline     -> 03_write/review.json          [bạn duyệt]
4 MEASURE    ZeroTTS đọc thật từng segment; lệch 40-50% hoặc đánh giá cuối 10-20 s thì gửi WRITE tự sửa
5 RENDER     cắt shot theo từng câu đọc, viền đen + watermark, trộn giọng với âm gốc, ghép
6 QC         kiểm tra thời lượng/codec, giải mã toàn bộ -> jobs/<job>/final_review.mp4
```

Bản Windows cũ (`review_firm_china/`, `dashboard/`) giữ ở tag `windows-legacy` (`git checkout windows-legacy`).

## Cài đặt

Cần: Linux x86_64 hoặc aarch64, Internet lúc cài, khoảng 3 GB đĩa cho phần mềm và model (thêm chỗ cho phim
và file dựng), tài khoản Antigravity cho `agy`. Không cần sudo.

```bash
git clone https://github.com/TranNguyenAnhKhoa/review_firm_harness.git
cd review_firm_harness && ./setup.sh
```

Lần đầu mất khoảng 2-10 phút tuỳ mạng (bản thử trên máy có mạng nhanh: 115 s). `setup.sh` làm lần lượt:

1. Tìm Python 3.10-3.13 và FFmpeg có libx264 + libass. Máy thiếu thì tạo môi trường riêng `.tools/conda`
   (dùng mamba/conda có sẵn, không có thì tự tải micromamba).
2. Tạo `.venv`, cài gói theo `requirements.txt` (phiên bản ghim cứng).
3. Tải model ZeroTTS (870 MB) vào `models/zerotts/ZeroTTS-c2bfbd67`. Sau đó đọc giọng offline.
4. Tự kiểm tra, giống `./run.sh doctor`.
5. Kiểm tra `agy` (Antigravity CLI) đã cài và đăng nhập chưa, bằng một lệnh rất ngắn.
6. Bật dashboard chạy nền tại http://127.0.0.1:8790 (systemd --user, không có thì nohup) và mở trình duyệt
   nếu máy có màn hình. Dashboard vẫn chạy khi đóng terminal hay logout.

Bước 5 báo agy chưa đăng nhập thì chạy `agy` một lần (đăng nhập trong cửa sổ đó), rồi chạy lại `./setup.sh`.

Tuỳ chọn: `--port N` (đổi cổng), `--no-start` (không bật dashboard), `--no-model`, `--no-agent-check`,
`--with-optional` (thêm edge-tts, faster-whisper), `--conda` (bỏ qua Python/FFmpeg của hệ thống).

## Dùng lần đầu

1. Mở http://127.0.0.1:8790 (máy từ xa: xem mục dưới).
2. Bấm **+ Job mới**: đặt tên job, chọn video bằng **Duyệt thư mục...** hoặc gõ đường dẫn, chọn giọng, bấm
   **Tạo job**. Harness chạy Probe + READ rồi dừng ở cổng duyệt READ.
3. Bấm ô **READ**, mở `timeline.md`, đọc. Đúng thì **Duyệt & chạy tiếp**. Sai thì ghi lý do rồi **Từ chối**,
   sau đó bấm **Chạy từ đây**: agent đọc lý do và làm lại.
4. Làm tương tự với `review.json` ở ô **WRITE**.
5. MEASURE, RENDER, QC tự chạy. Video cuối hiện ở ô **QC** và tab **Job**, file nằm ở
   `jobs/<job>/final_review.mp4`.

Có thể sửa tay `timeline.md` hoặc `review.json` trước khi duyệt. Sửa sau khi đã duyệt thì cổng mở lại và
các bước sau được đánh dấu cần chạy lại.

## Mở dashboard từ máy khác

Dashboard chỉ nghe ở 127.0.0.1. Từ máy của bạn mở tunnel SSH tới máy chạy harness:

```bash
ssh -L 8790:127.0.0.1:8790 <user>@<may-chay-harness>    # rồi mở http://127.0.0.1:8790
```

VS Code Remote-SSH tự chuyển cổng: mở tab Ports, thêm 8790.

## Dòng lệnh

Mọi việc trên dashboard đều làm được bằng `./run.sh`:

```bash
./run.sh new tap-01 /data/phim/tap01.mp4 --title "Tên phim - Tập 1" --voice baotrang
./run.sh run tap-01                        # chạy tới cổng duyệt kế tiếp (bỏ qua bước đã xong)
./run.sh status                            # tất cả job; ./run.sh status tap-01 cho một job
./run.sh approve tap-01 read               # hoặc: ./run.sh reject tap-01 read --note "thiếu đoạn 20:00-25:00"
./run.sh run tap-01 --only measure         # chạy riêng một bước
./run.sh run tap-01 --from write --force   # chạy lại từ WRITE, gọi agent lại
./run.sh check tap-01                      # kiểm tra review.json, ước tính thời lượng đọc
./run.sh import tap-01 timeline file.md    # nhập tay timeline/review (engine manual)
./run.sh brief /data/phim/tap01.mp4        # ngân sách thời lượng của một video
./run.sh voice --text "Câu thử giọng." --voice giahuy --out /tmp/thu.wav
./run.sh doctor                            # kiểm tra môi trường
```

Dashboard chạy nền: `./service.sh status | logs | restart | stop | uninstall`. Chạy ở terminal thay vì nền:
`./start.sh` (Ctrl+C để tắt).

## Dashboard

- **Danh sách job**: thẻ từng job, thanh tiến độ 6 bước, trạng thái (đang chạy / chờ duyệt / lỗi / xong).
- **Pipeline**: mỗi bước là một ô có trạng thái, engine (agy / claude / codex / zerotts / ffmpeg), số liệu chính
  (độ phủ timeline, ước tính và số đo thời lượng, tiến độ TTS/dựng), thời gian và token của agent. Bước có
  đầu vào đổi sau lần chạy trước được đánh dấu "cần chạy lại".
- **Chi tiết**: lỗi, cảnh báo, file kết quả (Markdown/JSON, ảnh sheet, proxy video, audio từng segment), cổng
  duyệt, ô dán kết quả tay, đổi agent/model cho READ và WRITE.
- **Log**: log trực tiếp của run đang chạy và các run trước; nút **Dừng** dừng cả agent và FFmpeg.
- **Job**: video nguồn, cài đặt (giọng, watermark, âm nền, cổng duyệt, số vòng tự sửa), lịch sử, lưu trữ job
  (chuyển vào `jobs/.trash/`, khôi phục được).
- **Hệ thống**: kiểm tra môi trường như `./run.sh doctor`.

Giao diện mở ở chế độ sáng, nút **Tối** để đổi. Trang HTML thuần ASCII nên hiển thị đúng cả khi trình duyệt
đoán sai bảng mã.

An toàn: dashboard từ chối Host lạ (chống DNS rebinding), chỉ nhận lệnh ghi từ chính trang của nó (header
`X-Harness` và kiểm tra Origin), không gửi header CORS, chỉ phục vụ file trong thư mục job, và chỉ khởi chạy
lệnh `python -m harness run` với tham số đã kiểm tra. Dashboard không có đăng nhập: đừng mở ra mạng
(`HARNESS_HOST=0.0.0.0`) nếu người khác vào được cổng đó.

## Agent làm gì, thấy gì

| Bước | agy (mặc định) | claude / codex |
| --- | --- | --- |
| READ | Xem proxy 360p, mỗi đoạn 10 phút, timecode nguồn in ở góc trái trên | Xem sheet khung hình 4x4 có giờ, sheet dải phụ đề cứng, transcript Whisper nếu bật |
| WRITE | Đọc timeline đã duyệt, quy tắc biên tập, mẫu JSON, danh sách cắt cảnh | Như agy; claude còn tự chạy `./run.sh check` |

Prompt của từng bước liệt kê đúng các file được mở và các bước phải làm. Agent chạy từ thư mục harness (đọc
`AGENTS.md`) và chỉ được ghi một file trong thư mục job. agy chỉ dùng tool đọc/ghi file: ở chế độ nền, lệnh
shell bị từ chối và phiên dừng luôn. claude được đúng 2 lệnh shell: `./run.sh frame` (khung hình đầy đủ ở một
giây bất kỳ) và `./run.sh check`. Kết quả READ/WRITE được kiểm tra tự động (front matter, bảng timeline có
start/end, schema review, cấu trúc đánh giá cuối). Sai thì agent được yêu cầu sửa, tối đa
`agents.write.fix_rounds` lần.

Đổi agent cho một job: ô READ hoặc WRITE, mục **Agent cho bước này**. Đổi mặc định cho mọi job:
`agents.read.engine` và `agents.write.engine` trong `config/default.yaml`. Dùng claude/codex thì phải đăng nhập
CLI đó trên máy chạy harness.

## Giọng đọc

Model ZeroTTS có 8 giọng: `baotrang` (mặc định, giọng của mẫu 1004), `maichi`, `kimoanh`, `hamy` (nữ);
`giahuy`, `huuduc`, `quangminh`, `tiendat` (nam). Chọn khi tạo job hoặc trong tab **Job**. Nghe thử:
`./run.sh voice --text "..." --voice <id> --out /tmp/thu.wav`. Preset cảm xúc và nhịp đọc:
[docs/voice-and-emotion.md](docs/voice-and-emotion.md).

## Cấu hình

- `config/default.yaml`: mọi cài đặt (agent, cổng duyệt, giọng, khung hình, âm lượng, quy tắc thời lượng).
- `jobs/<job>/config.yaml`: ghi đè cho một job; dashboard ghi vào file này.
- `.env` (chép từ `.env.example`): `HARNESS_PORT`, `HARNESS_HOST`, `HARNESS_MEDIA_DIRS` (thư mục mà nút
  **Duyệt thư mục...** được liệt kê, mặc định `media/`, `~/Videos`, `~`), `HARNESS_JOBS_DIR`, `FFMPEG_BINARY`.
  Sửa `.env` xong chạy `./service.sh install` để dashboard nhận cổng/host mới.

Quy tắc biên tập: [docs/editorial-guidelines.md](docs/editorial-guidelines.md). Mẫu dựng 1004:
[docs/reference-1004.md](docs/reference-1004.md).

## Cập nhật và gỡ

```bash
git pull && ./setup.sh     # bước đã xong được dùng lại; dashboard khởi động lại với code mới
```

Run đang chạy không bị dừng khi dashboard khởi động lại.

Gỡ: `./service.sh uninstall`, rồi xoá thư mục harness. Phim và kết quả nằm trong `jobs/` và `media/`:
chép ra ngoài trước nếu cần giữ.

## Xử lý sự cố

| Hiện tượng | Cách sửa |
| --- | --- |
| Bước 5 của setup báo agy chưa đăng nhập | Chạy `agy`, đăng nhập, rồi `./setup.sh` lại |
| READ/WRITE lỗi "Agent không ghi timeline.md / review.json" | Xem tab **Log** và `jobs/<job>/02_read/agent_*.jsonl`; lỗi đăng nhập thì như dòng trên |
| claude báo "Failed to authenticate" | `claude auth login`, hoặc đổi bước đó sang agy |
| Dashboard không mở được | `./service.sh status` và `./service.sh logs`; cổng bận thì `./setup.sh --port 8791` |
| Dashboard không tự lên sau reboot | `sudo loginctl enable-linger $USER`, hoặc sau mỗi lần reboot chạy `./service.sh start` |
| MEASURE lỗi "ZeroTTS model could not be loaded" | Xoá `models/zerotts/` rồi `./setup.sh` (model phải là file thường, không symlink) |
| MEASURE "CHƯA ĐẠT" sau các vòng tự sửa | Xem bảng từng segment ở ô MEASURE, sửa `review.json` (thêm/bớt câu kể), duyệt lại WRITE, chạy tiếp |
| Video nguồn đã chuyển chỗ | Sửa `source.path` trong `jobs/<job>/job.json` |

## Thư mục

```
config/default.yaml   mọi cài đặt
prompts/              prompt READ và WRITE (có chỗ điền {{...}})
docs/                 quy tắc biên tập, giọng đọc, mẫu 1004
harness/              package Python: pipeline/ (job, stages, runner, agents), audio/, video/, monitor/ (dashboard)
jobs/<job>/           job.json, config.yaml, state.json, events.jsonl, runs/*.log,
                      01_probe ... 06_qc, final_review.mp4
media/                chỗ đặt video nguồn (không vào git)
models/ .tools/ .venv/   do setup.sh tạo (không vào git)
tests/                61 test
```

Video nằm trong `media/` được lưu bằng đường dẫn tương đối, nên chép cả thư mục harness sang máy khác vẫn chạy.

## Job chuyển từ bản Windows

`jobs/ga_kim_thoa_ep01` giữ timeline (Antigravity Desktop) và `review.json` 65 segment của bản cũ, đang chờ
duyệt READ. Để chạy tiếp: chép video vào `media/ga_kim_thoa_ep01.mp4`, chạy bước Probe, rồi duyệt READ và
WRITE. Timeline cũ chỉ có 10 dòng cho 48 phút và không có bảng shot, nên chạy lại READ bằng agy (nút
**Chạy lại (force)** ở ô READ) sẽ có nhiều shot gợi ý hơn.

## Lưu ý

- `render.picture_style.fit_mode: cover` (mặc định, theo mẫu 1004) cắt bớt trên/dưới khung nguồn, có thể mất
  một phần phụ đề cứng sát đáy. `contain` giữ nguyên khung.
- Số giây do TTS đo và file đã dựng là căn cứ cuối. Harness không đệm im lặng hay đọc chậm để đủ tỷ lệ.
- Câu đùa và nhận xét vẫn cần người xem lại: code chỉ kiểm tra cấu trúc và thời lượng.

## Việc cần cải tiến

Danh sách đã xếp thứ tự, có căn cứ và ước lượng thời gian: [docs/ROADMAP.md](docs/ROADMAP.md).

## Phát triển

```bash
.venv/bin/python -m unittest discover -s tests     # 61 test, khoảng 10 s, không cần mạng hay agent
```

Sửa giao diện ở `harness/monitor/static/index.src.html`, rồi chạy `.venv/bin/python -m harness.monitor.asciify`
để tạo lại `index.html` thuần ASCII (test báo lỗi nếu quên). Quy tắc cho agent và người sửa code: `AGENTS.md`.
