#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="milkway-bot"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_USER="${SUDO_USER:-$USER}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    echo "프로젝트 루트에서 실행할 수 없습니다: $PROJECT_ROOT" >&2
    exit 1
fi

sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip

cd "$PROJECT_ROOT"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo ".env 파일을 만들었습니다. 토큰과 API 키를 입력한 뒤 이 스크립트를 다시 실행하세요." >&2
    exit 1
fi

sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<UNIT
[Unit]
Description=Milkway Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_ROOT}
EnvironmentFile=${PROJECT_ROOT}/.env
ExecStart=${PROJECT_ROOT}/.venv/bin/python -m discord_bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"

echo "Oracle Cloud VM에 ${SERVICE_NAME} 서비스를 설치하고 실행했습니다."
echo "상태: sudo systemctl status ${SERVICE_NAME}"
echo "로그: sudo journalctl -u ${SERVICE_NAME} -f"
