#!/usr/bin/env bash
# One-time setup on Linux (no sudo needed):
#   1. Python 3.10-3.13 + FFmpeg with libx264/libass. System ones are used when good enough;
#      otherwise a private conda env is created in .tools/conda (mamba/conda if present, else micromamba
#      is downloaded into .tools/bin).
#   2. .venv with pinned packages (requirements.txt, optionally requirements-optional.txt).
#   3. ZeroTTS model weights (~870 MB) into models/zerotts, so TTS then runs offline.
#
#   ./setup.sh [--with-optional] [--no-model] [--conda]
#     --with-optional  also install edge-tts + faster-whisper
#     --no-model       skip the model download
#     --conda          always use the private conda env (ignore system Python/FFmpeg)
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
WITH_OPTIONAL=0; NO_MODEL=0; FORCE_CONDA=0
for arg in "$@"; do
  case "$arg" in
    --with-optional) WITH_OPTIONAL=1 ;;
    --no-model) NO_MODEL=1 ;;
    --conda) FORCE_CONDA=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Tham số lạ: $arg (xem ./setup.sh --help)" >&2; exit 2 ;;
  esac
done
say() { printf '\n== %s\n' "$*"; }

ffmpeg_ok() {  # $1 = ffmpeg binary
  local conf; conf="$("$1" -hide_banner -buildconf 2>/dev/null)" || return 1
  grep -q enable-libx264 <<<"$conf" && grep -q enable-libass <<<"$conf" && grep -q enable-libmp3lame <<<"$conf"
}
python_ok() {  # $1 = python binary
  "$1" -c 'import sys, venv, ensurepip; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)' 2>/dev/null
}

say "1/4 Python và FFmpeg"
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
    echo "Hệ thống thiếu Python 3.10-3.13 hoặc FFmpeg có libx264/libass: tạo môi trường riêng $CONDA_ENV"
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
        *) echo "Không hỗ trợ kiến trúc $(uname -m): cài ffmpeg (có libx264, libass) và python3.11 bằng tay" >&2; exit 1 ;;
      esac
      echo "Tải micromamba ($PLATFORM) vào .tools/bin"
      mkdir -p "$ROOT/.tools"
      curl -fsSL "https://micro.mamba.pm/api/micromamba/$PLATFORM/latest" | tar -xj -C "$ROOT/.tools" bin/micromamba
      SOLVER="$ROOT/.tools/bin/micromamba"
    fi
    export MAMBA_ROOT_PREFIX="$ROOT/.tools/mamba-root"
    "$SOLVER" create -y -q -p "$CONDA_ENV" -c conda-forge --override-channels python=3.11 "ffmpeg=*=gpl*"
  fi
  ffmpeg_ok "$CONDA_ENV/bin/ffmpeg" || { echo "FFmpeg trong $CONDA_ENV thiếu libx264/libass/libmp3lame" >&2; exit 1; }
  PY="$CONDA_ENV/bin/python"
fi
echo "Python: $PY ($("$PY" --version 2>&1))"
if [ "$SYSTEM_FFMPEG" = 1 ] && [ ! -x "$CONDA_ENV/bin/ffmpeg" ]; then echo "FFmpeg: $(command -v ffmpeg)"; else echo "FFmpeg: $CONDA_ENV/bin/ffmpeg"; fi

say "2/4 Môi trường Python .venv"
if [ -x .venv/bin/python ] && ! python_ok .venv/bin/python; then
  echo ".venv cũ dùng Python không hỗ trợ: tạo lại"; rm -rf .venv
fi
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt
if [ "$WITH_OPTIONAL" = 1 ]; then .venv/bin/python -m pip install -q -r requirements-optional.txt; fi
.venv/bin/python -m pip check

say "3/4 Model ZeroTTS"
if [ "$NO_MODEL" = 1 ]; then echo "Bỏ qua (--no-model)"; else .venv/bin/python -m harness.setup_model; fi

say "4/4 Kiểm tra"
mkdir -p jobs media
.venv/bin/python -m harness.monitor.asciify --check
.venv/bin/python -m harness doctor || true
cat <<EOF

Xong. Tiếp theo:
  ./start.sh                                  dashboard http://127.0.0.1:8790
  ./run.sh new <ten-job> /duong/dan/phim.mp4  tạo job (hoặc nút "+ Job mới" trên dashboard)
  ./service.sh install                        chạy dashboard nền (sống qua logout)
EOF
