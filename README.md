# 🌌 Milkway Bot

대학생활 일정, 서버 관리, 무료 질문·검색 기능을 짧고 직관적인 슬래시 명령어로 사용하는 Discord 봇입니다.

## 정식 초대 링크

[Milkway Bot을 Discord 서버에 초대하기](https://discord.com/oauth2/authorize?client_id=1533024340155699290&permissions=1374658194518&integration_type=0&scope=bot%20applications.commands)

## 주요 명령어

| 분류 | 명령어 |
|---|---|
| 학교 | `/학교 오늘`, `/학교 학점`, `/학교 집중` |
| 과제 | `/과제 추가`, `/과제 목록`, `/과제 완료`, `/과제 삭제` |
| 시험 | `/시험 추가`, `/시험 목록`, `/시험 삭제` |
| 시간표 | `/시간표 추가`, `/시간표 오늘`, `/시간표 전체`, `/시간표 삭제` |
| 질문·검색 | `/질문`, `/검색`, `/요약`, `/퀴즈`, `/상태` |
| 알림 | `/알림 후에`, `/알림 날짜`, `/알림 목록`, `/알림 삭제` |
| 예약 | `/예약 반복`, `/예약 매일`, `/예약 매주`, `/예약 한번`, `/예약 목록`, `/예약 삭제` |
| 전송 | `/전송`, `/공지`, `/투표` |
| 설정 | `/설정 시간대`, `/설정 환영`, `/설정 퇴장`, `/설정 역할`, `/설정 로그`, `/설정 끄기`, `/설정 확인` |
| 관리 | `/관리 정리`, `/관리 제한`, `/관리 제한해제`, `/관리 추방`, `/관리 차단`, `/관리 차단해제`, `/관리 슬로우`, `/관리 경고`, `/관리 경고목록`, `/관리 경고초기화` |
| 기타 | `/도움말`, `/초대`, `/핑`, `/서버`, `/사용자`, `/아바타`, `/선택`, `/주사위`, `/동전`, `/시간` |

## 환경설정

`.env.example`을 `.env`로 복사한 뒤 실제 값을 입력합니다.

```env
DISCORD_TOKEN=Discord_봇_토큰
DEV_GUILD_ID=명령어를_쓸_서버_ID
BOT_DISPLAY_NAME=Milkway Bot
DATABASE_PATH=data/bot.db
LOG_LEVEL=INFO
ENABLE_MEMBER_INTENT=true
ENABLE_MESSAGE_CONTENT_INTENT=true

AI_PROVIDER=groq
GROQ_API_KEY=gsk_실제_키
GROQ_MODEL=auto
GROQ_SEARCH_MODEL=groq/compound-mini

GEMINI_API_KEY=
GEMINI_MODEL=auto
AI_MAX_OUTPUT_TOKENS=1200
AI_DAILY_USER_LIMIT=20
```

Groq 키가 있으면 일반 질문에는 계정에 실제로 열린 모델을 자동 선택하고, `/검색`에는 `groq/compound-mini`를 사용합니다.

## Windows 설치 및 시험

```powershell
cd $HOME\Desktop
curl.exe -L "https://github.com/smini131-maker/milkway-bot/archive/refs/heads/main.zip" -o "milkway-bot.zip"
Expand-Archive -Path ".\milkway-bot.zip" -DestinationPath "." -Force
cd .\milkway-bot-main
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
Copy-Item .env.example .env
notepad .env
python -m discord_bot
```

Windows가 종료되거나 절전 상태가 되면 봇도 오프라인이 됩니다.

버전 확인:

```powershell
python -c "import discord_bot; print(discord_bot.__version__)"
```

현재 버전:

```text
1.5.4
```

## Google Cloud Always Free 24시간 실행

Google Cloud Compute Engine 무료 등급의 `e2-micro` VM을 사용합니다. 무료 대상 리전은 `us-west1`, `us-central1`, `us-east1` 중 하나여야 하며, 부팅 디스크는 표준 영구 디스크 30GB 이하로 설정합니다.

권장 VM 설정:

```text
이름: milkway-bot
리전: us-west1 / us-central1 / us-east1 중 하나
머신 유형: e2-micro
이미지: Debian 12 또는 Ubuntu 24.04 LTS
부팅 디스크: Standard persistent disk, 30GB 이하
```

VM을 만든 뒤 Google Cloud 콘솔의 `SSH` 버튼으로 접속합니다.

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/smini131-maker/milkway-bot.git
cd milkway-bot
cp .env.example .env
nano .env
bash deploy/install-google-cloud.sh
```

설치 스크립트는 e2-micro의 약 1GB 메모리를 보완하기 위해 1GB 스왑을 만들고, `systemd` 부팅 자동 실행과 오류 자동 재시작을 설정합니다.

상태 확인:

```bash
sudo systemctl status milkway-bot --no-pager
sudo systemctl is-enabled milkway-bot
sudo systemctl is-active milkway-bot
```

실시간 로그:

```bash
sudo journalctl -u milkway-bot -f
```

업데이트:

```bash
cd ~/milkway-bot
git pull
.venv/bin/python -m pip install -e .
sudo systemctl restart milkway-bot
```

SQLite 데이터는 VM의 `data/bot.db`에 저장됩니다. VM을 삭제하기 전에는 반드시 백업하세요.

## 질문·검색 확인

Discord에서 순서대로 실행합니다.

```text
/상태
/질문
/검색
```

`/상태`에는 현재 공급자, 일반 모델, 검색 모델이 표시됩니다.

## 보안

- `.env`, Discord Bot Token, Groq API Key, Gemini API Key를 GitHub에 올리지 마세요.
- 키가 노출되면 즉시 해당 공급자 콘솔에서 폐기하고 새로 만드세요.
- 질문 기능에 학번, 비밀번호, 연락처 같은 민감정보를 입력하지 마세요.

## 테스트

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

## 라이선스

MIT License
