#!/usr/bin/env bash
# Run the dashboard as a background service that survives Ctrl+C, a closed terminal and logout.
#   ./service.sh install | start | stop | restart | status | logs [-f] | uninstall
# Backend: a systemd --user unit when a user manager is reachable (survives reboot with
# `loginctl enable-linger $USER`), otherwise nohup + PID file in .run/ (re-run start after a reboot).
# Force one with SERVICE_BACKEND=systemd|nohup. Port/host from .env (HARNESS_PORT, HARNESS_HOST).
# Pipeline runs started from the dashboard are separate processes: stopping the service does not stop them.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd -P)"
NAME="review-harness"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
RUN_DIR="$ROOT/.run"
PID_FILE="$RUN_DIR/$NAME.pid"
LOG_FILE="$RUN_DIR/$NAME.log"
PYTHON="$ROOT/.venv/bin/python"
[ -x "$PYTHON" ] || { echo "Thiếu .venv: chạy ./setup.sh" >&2; exit 2; }
if [ -f .env ]; then set -a; . ./.env; set +a; fi
PORT="${HARNESS_PORT:-8790}"; HOST="${HARNESS_HOST:-127.0.0.1}"
case "$PORT" in ''|*[!0-9]*) echo "HARNESS_PORT phải là số" >&2; exit 2 ;; esac

have_systemd() { command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; }
BACKEND="${SERVICE_BACKEND:-}"
[ -n "$BACKEND" ] || { if have_systemd; then BACKEND=systemd; else BACKEND=nohup; fi; }

pid_alive() {
  [ -f "$PID_FILE" ] || return 1
  local pid; pid="$(cat "$PID_FILE")"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q 'harness serve'
}

unit() {
  cat <<EOF
[Unit]
Description=Review harness dashboard ($ROOT)
After=network.target

[Service]
WorkingDirectory=$ROOT
Environment=PYTHONPATH=$ROOT
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-$ROOT/.env
ExecStart=$PYTHON -m harness serve --host $HOST --port $PORT --no-browser
Restart=on-failure
RestartSec=3
KillMode=process

[Install]
WantedBy=default.target
EOF
}

case "${1:-}" in
  install)   # (re)install and (re)start, so a re-run picks up new code and settings
    if [ "$BACKEND" = systemd ]; then
      mkdir -p "$UNIT_DIR"; unit > "$UNIT_DIR/$NAME.service"
      systemctl --user daemon-reload
      systemctl --user enable "$NAME.service" >/dev/null 2>&1
      systemctl --user restart "$NAME.service"
      if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" != yes ]; then
        loginctl enable-linger "$USER" >/dev/null 2>&1 || true
      fi
      if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" = yes ]; then
        echo "systemd --user: $NAME.service chạy trên http://$HOST:$PORT, tự bật lại sau reboot"
      else
        echo "systemd --user: $NAME.service chạy trên http://$HOST:$PORT (tự bật sau reboot cần: sudo loginctl enable-linger $USER)"
      fi
    else
      "$0" stop >/dev/null 2>&1 || true
      "$0" start
    fi ;;
  start)
    if [ "$BACKEND" = systemd ]; then systemctl --user start "$NAME.service"; exit 0; fi
    mkdir -p "$RUN_DIR"
    if pid_alive; then echo "Đang chạy (pid $(cat "$PID_FILE"))"; exit 0; fi
    PYTHONPATH="$ROOT" PYTHONUNBUFFERED=1 nohup "$PYTHON" -m harness serve --host "$HOST" --port "$PORT" --no-browser \
      >>"$LOG_FILE" 2>&1 < /dev/null &
    echo $! > "$PID_FILE"; sleep 1
    if pid_alive; then echo "nohup: đang chạy (pid $(cat "$PID_FILE")) trên http://$HOST:$PORT, log $LOG_FILE"
    else echo "Không khởi động được, xem $LOG_FILE" >&2; tail -5 "$LOG_FILE" >&2; exit 1; fi ;;
  stop)
    if [ "$BACKEND" = systemd ]; then systemctl --user stop "$NAME.service"; exit 0; fi
    if pid_alive; then kill "$(cat "$PID_FILE")"; rm -f "$PID_FILE"; echo "Đã dừng"; else echo "Không chạy"; fi ;;
  restart) "$0" stop; "$0" start ;;
  status)
    if [ "$BACKEND" = systemd ]; then systemctl --user status "$NAME.service" --no-pager || true
    elif pid_alive; then echo "nohup: đang chạy (pid $(cat "$PID_FILE")) http://$HOST:$PORT"; else echo "nohup: không chạy"; fi ;;
  logs)
    shift
    if [ "$BACKEND" = systemd ]; then journalctl --user -u "$NAME.service" --no-pager -n 100 "$@"
    else tail -n 100 "$@" "$LOG_FILE"; fi ;;
  uninstall)
    if [ "$BACKEND" = systemd ]; then
      systemctl --user disable --now "$NAME.service" 2>/dev/null || true
      rm -f "$UNIT_DIR/$NAME.service"; systemctl --user daemon-reload; echo "Đã gỡ unit"
    else "$0" stop; fi ;;
  *) sed -n '2,7p' "$0"; exit 2 ;;
esac
