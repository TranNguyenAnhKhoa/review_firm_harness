#!/usr/bin/env bash
# One command after `git clone`: installs everything and starts the dashboard. No sudo needed.
#
#   git clone https://github.com/TranNguyenAnhKhoa/review_firm_harness.git
#   cd review_firm_harness && ./setup.sh
#
# Steps (safe to re-run; finished steps are reused):
#   1. Python 3.10-3.13 + FFmpeg with libx264/libass/libmp3lame. System ones are used when good enough;
#      otherwise a private env is created in .tools/conda (mamba/conda if present, else micromamba is
#      downloaded into .tools/bin).
#   2. .venv with pinned packages (requirements.txt; --with-optional adds requirements-optional.txt).
#   3. ZeroTTS model (~870 MB) into models/zerotts, so speech then runs offline.
#   4. Self-check (./run.sh doctor).
#   5. agy (Antigravity CLI, the READ/WRITE agent): installed and logged in?
#   6. Dashboard as a background service (systemd --user, else nohup) on http://127.0.0.1:8790.
#
#   ./setup.sh [--with-optional] [--no-model] [--conda] [--no-agent-check] [--no-start] [--port N]
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
WITH_OPTIONAL=0; NO_MODEL=0; FORCE_CONDA=0; AGENT_CHECK=1; START=1
if [ -f .env ]; then set -a; . ./.env; set +a; fi
PORT="${HARNESS_PORT:-8790}"
while [ $# -gt 0 ]; do
  case "$1" in
    --with-optional) WITH_OPTIONAL=1 ;;
    --no-model) NO_MODEL=1 ;;
    --conda) FORCE_CONDA=1 ;;
    --no-agent-check) AGENT_CHECK=0 ;;
    --no-start) START=0 ;;
    --port) PORT="$2"; shift ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "Tham số lạ: $1 (xem ./setup.sh --help)" >&2; exit 2 ;;
  esac
  shift
done
case "$PORT" in ''|*[!0-9]*) echo "--port phải là số" >&2; exit 2 ;; esac
export HARNESS_PORT="$PORT"
STARTED=$(date +%s)
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
WARNINGS=()

ffmpeg_ok() {  # $1 = ffmpeg binary
  local conf; conf="$("$1" -hide_banner -buildconf 2>/dev/null)" || return 1
  grep -q enable-libx264 <<<"$conf" && grep -q enable-libass <<<"$conf" && grep -q enable-libmp3lame <<<"$conf"
}
python_ok() {  # $1 = python binary: 3.10-3.13 with a working venv/ensurepip
  "$1" -c 'import sys, venv, ensurepip; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)' 2>/dev/null
}
fetch() {  # $1 = URL, $2 = destination file
  if command -v curl >/dev/null; then curl -fsSL --retry 3 -o "$2" "$1"
  elif command -v wget >/dev/null; then wget -q -O "$2" "$1"
  elif command -v python3 >/dev/null; then python3 -c 'import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])' "$1" "$2"
  else echo "Cần curl, wget hoặc python3 để tải $1" >&2; return 1; fi
}

# ---- 1. Python + FFmpeg -----------------------------------------------------------------------------
say "1/6 Python và FFmpeg"
PY=""
if [ "$FORCE_CONDA" = 0 ]; then
  for candidate in python3.12 python3.11 python3.13 python3.10 python3; do
    if command -v "$candidate" >/dev/null && python_ok "$(command -v "$candidate")"; then PY="$(command -v "$candidate")"; break; fi
  done
fi
SYSTEM_FFMPEG=0
if [ "$FORCE_CONDA" = 0 ] && command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && ffmpeg_ok "$(command -v ffmpeg)"; then
  SYSTEM_FFMPEG=1
fi
CONDA_ENV="$ROOT/.tools/conda"
if [ -z "$PY" ] || [ "$SYSTEM_FFMPEG" = 0 ]; then
  if [ -x "$CONDA_ENV/bin/python" ] && [ -x "$CONDA_ENV/bin/ffmpeg" ] && ffmpeg_ok "$CONDA_ENV/bin/ffmpeg"; then
    echo "Dùng lại môi trường riêng $CONDA_ENV"
  else
    echo "Máy thiếu Python 3.10-3.13 (có venv) hoặc FFmpeg có libx264/libass: tạo môi trường riêng $CONDA_ENV (vài phút)"
    SOLVER=""
    for candidate in micromamba mamba conda "$HOME/miniforge3/bin/mamba" "$HOME/mambaforge/bin/mamba" \
                     "$HOME/miniconda3/bin/conda" "$HOME/anaconda3/bin/conda" "$ROOT/.tools/bin/micromamba"; do
      if command -v "$candidate" >/dev/null 2>&1; then SOLVER="$(command -v "$candidate")"; break; fi
      if [ -x "$candidate" ]; then SOLVER="$candidate"; break; fi
    done
    if [ -z "$SOLVER" ]; then
      case "$(uname -m)" in
        x86_64) PLATFORM=linux-64 ;;
        aarch64|arm64) PLATFORM=linux-aarch64 ;;
        *) echo "Kiến trúc $(uname -m) chưa hỗ trợ: cài ffmpeg (libx264, libass) và python3.11 rồi chạy lại" >&2; exit 1 ;;
      esac
      echo "Tải micromamba ($PLATFORM) vào .tools/bin"
      mkdir -p "$ROOT/.tools/bin"
      fetch "https://micro.mamba.pm/api/micromamba/$PLATFORM/latest" "$ROOT/.tools/micromamba.tar.bz2"
      if ! tar -xjf "$ROOT/.tools/micromamba.tar.bz2" -C "$ROOT/.tools" bin/micromamba 2>/dev/null; then
        python3 -c 'import sys, tarfile; tarfile.open(sys.argv[1]).extract("bin/micromamba", sys.argv[2])' \
          "$ROOT/.tools/micromamba.tar.bz2" "$ROOT/.tools"
      fi
      rm -f "$ROOT/.tools/micromamba.tar.bz2"
      chmod +x "$ROOT/.tools/bin/micromamba"
      SOLVER="$ROOT/.tools/bin/micromamba"
    fi
    export MAMBA_ROOT_PREFIX="$ROOT/.tools/mamba-root"
    "$SOLVER" create -y -q -p "$CONDA_ENV" -c conda-forge --override-channels python=3.11 "ffmpeg=*=gpl*"
  fi
  ffmpeg_ok "$CONDA_ENV/bin/ffmpeg" || { echo "FFmpeg trong $CONDA_ENV thiếu libx264/libass/libmp3lame" >&2; exit 1; }
  PY="$CONDA_ENV/bin/python"
fi
echo "Python: $PY ($("$PY" --version 2>&1))"
if [ -x "$CONDA_ENV/bin/ffmpeg" ]; then echo "FFmpeg: $CONDA_ENV/bin/ffmpeg"; else echo "FFmpeg: $(command -v ffmpeg)"; fi

# ---- 2. .venv ---------------------------------------------------------------------------------------
say "2/6 Môi trường Python .venv"
if [ -x .venv/bin/python ] && ! python_ok .venv/bin/python; then
  echo ".venv cũ dùng Python không hỗ trợ: tạo lại"; rm -rf .venv
fi
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -m pip install -q --disable-pip-version-check --upgrade pip
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
if [ "$WITH_OPTIONAL" = 1 ]; then .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements-optional.txt; fi
.venv/bin/python -m pip check

# ---- 3. model ---------------------------------------------------------------------------------------
say "3/6 Model ZeroTTS"
if [ "$NO_MODEL" = 1 ]; then echo "Bỏ qua (--no-model)"; else .venv/bin/python -m harness.setup_model; fi

# ---- 4. self-check ----------------------------------------------------------------------------------
say "4/6 Kiểm tra môi trường"
mkdir -p jobs media
.venv/bin/python -m harness.monitor.asciify --check
.venv/bin/python -m harness doctor || WARNINGS+=("Còn mục THIẾU ở bước 4 (./run.sh doctor)")

# ---- 5. agent ---------------------------------------------------------------------------------------
say "5/6 Agent agy (READ/WRITE)"
if ! command -v agy >/dev/null; then
  warn "Chưa có lệnh agy trên PATH. Cài Antigravity CLI, chạy 'agy' một lần để đăng nhập, rồi chạy lại ./setup.sh."
  WARNINGS+=("Chưa có agy: READ/WRITE sẽ lỗi cho tới khi cài và đăng nhập (hoặc chọn claude/codex/manual trên dashboard)")
elif [ "$AGENT_CHECK" = 0 ]; then
  echo "agy: $(command -v agy) (bỏ qua kiểm tra đăng nhập)"
else
  echo "agy: $(command -v agy). Thử một lệnh rất ngắn để kiểm tra đăng nhập..."
  PROBE="$(cd "$ROOT/media" && timeout 120 agy -p "Reply with the single word OK." --output-format stream-json 2>&1 || true)"
  if grep -q '"status":"SUCCESS"' <<<"$PROBE"; then
    echo "agy đã đăng nhập, chạy được ở chế độ nền."
  else
    warn "agy chưa chạy được ở chế độ nền:"
    grep -v '^{' <<<"$PROBE" | tail -3 >&2 || true
    warn "Chạy 'agy' (tương tác) một lần để đăng nhập, rồi chạy lại ./setup.sh."
    WARNINGS+=("agy chưa đăng nhập được: READ/WRITE sẽ lỗi")
  fi
fi

# ---- 6. dashboard -----------------------------------------------------------------------------------
say "6/6 Dashboard"
URL="http://127.0.0.1:$PORT/"
if [ "$START" = 0 ]; then
  echo "Bỏ qua (--no-start). Bật bằng: ./start.sh  hoặc  ./service.sh install"
else
  ./service.sh install
  ok=0
  for _ in $(seq 1 20); do
    if .venv/bin/python -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2)' "${URL}api/overview" 2>/dev/null; then ok=1; break; fi
    sleep 0.5
  done
  if [ "$ok" = 1 ]; then echo "Dashboard đang chạy: $URL"
    if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v xdg-open >/dev/null; then
      (xdg-open "$URL" >/dev/null 2>&1 &) || true
    fi
  else warn "Dashboard chưa trả lời ở $URL: xem ./service.sh logs (cổng $PORT bận? chạy lại với --port <số khác>)"
       WARNINGS+=("Dashboard chưa lên"); fi
fi

ELAPSED=$(( $(date +%s) - STARTED ))
say "Xong sau ${ELAPSED}s"
if [ ${#WARNINGS[@]} -gt 0 ]; then
  for w in "${WARNINGS[@]}"; do warn "- $w"; done
fi
cat <<EOF

Mở dashboard: $URL
  Máy này là server từ xa? Trên máy của bạn chạy: ssh -L $PORT:127.0.0.1:$PORT $(whoami)@$(hostname)
  rồi mở $URL
Tạo job: nút "+ Job mới" trên dashboard, hoặc ./run.sh new <ten-job> /duong/dan/phim.mp4
Dashboard chạy nền: ./service.sh status | logs | restart | stop
EOF
