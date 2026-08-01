#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
ENV_FILE="$PROJECT_ROOT/.env"
SERVICE_FILE="/etc/systemd/system/milkway-bot.service"
RUN_USER="${SUDO_USER:-$USER}"

if [[ ! -x "$PYTHON" ]]; then
  echo "가상환경을 찾을 수 없습니다: $PYTHON" >&2
  echo "먼저 python3 -m venv .venv && source .venv/bin/activate && pip install -e . 를 실행하세요." >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env 파일을 찾을 수 없습니다: $ENV_FILE" >&2
  exit 1
fi

sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=Milkway Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_ROOT
EnvironmentFile=$ENV_FILE
ExecStart=$PYTHON -m discord_bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now milkway-bot
sudo systemctl --no-pager --full status milkway-bot || true

echo "설치 완료: 부팅 시 자동 실행되고 오류 종료 시 자동 재시작합니다."
echo "로그 확인: sudo journalctl -u milkway-bot -f"
