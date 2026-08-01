# 🌌 Milkway Bot

대학생활 일정, 서버 관리, 무료 AI 질문·검색을 한글 슬래시 명령어로 사용하는 Discord 봇입니다.

## 정식 초대 링크

[Milkway Bot을 Discord 서버에 초대하기](https://discord.com/oauth2/authorize?client_id=1533024340155699290&permissions=1374658194518&integration_type=0&scope=bot%20applications.commands)

## 주요 명령어

| 분류 | 명령어 |
|---|---|
| 과제 | `/과제 추가`, `/과제 보기`, `/과제 완료`, `/과제 삭제` |
| 시험 | `/시험 추가`, `/시험 보기`, `/시험 삭제` |
| 시간표 | `/시간표 추가`, `/시간표 오늘`, `/시간표 보기`, `/시간표 삭제` |
| AI | `/인공지능 질문`, `/인공지능 검색`, `/인공지능 요약`, `/인공지능 퀴즈`, `/인공지능 사용량` |
| 알림 | `/알림 후에`, `/알림 날짜`, `/알림 보기`, `/알림 삭제` |
| 예약 | `/예약 간격`, `/예약 매일`, `/예약 매주`, `/예약 한번`, `/예약 보기`, `/예약 삭제` |
| 관리 | `/관리 삭제`, `/관리 타임아웃`, `/관리 추방`, `/관리 차단`, `/관리 경고` 등 |
| 기타 | `/도움말`, `/초대`, `/핑`, `/서버정보`, `/시간` 등 |

## 봇 표시 이름

기본 예시는 `Milkway Bot`입니다.

```env
BOT_DISPLAY_NAME=Milkway Bot
```

이 값을 비워두면 Discord Developer Portal과 서버에 설정된 현재 이름을 코드가 변경하지 않습니다.

```env
BOT_DISPLAY_NAME=
```

## 권장 무료 AI: Groq Cloud

Groq 무료 플랜은 일반 대화 모델과 웹 검색이 가능한 Compound 모델을 API 키로 사용할 수 있습니다. 봇은 `GROQ_API_KEY`가 있으면 Groq를 우선 사용하고, 일반 모델은 계정에 실제로 열린 모델 중에서 자동 선택합니다.

### Groq API 키 만들기

1. Groq Cloud Console에 로그인합니다.
2. `API Keys`로 이동합니다.
3. `Create API Key`를 누릅니다.
4. 생성된 `gsk_`로 시작하는 키를 복사합니다.
5. 키를 Discord, GitHub, 채팅에 공개하지 않습니다.

### `.env` 설정

```env
AI_PROVIDER=auto

GROQ_API_KEY=gsk_실제_키
GROQ_MODEL=auto
GROQ_SEARCH_MODEL=groq/compound-mini

# 기존 Gemini 키는 선택적으로 보조 공급자로 남겨둘 수 있습니다.
GEMINI_API_KEY=
GEMINI_MODEL=auto

AI_MAX_OUTPUT_TOKENS=1200
AI_DAILY_USER_LIMIT=20
```

`AI_PROVIDER=auto`는 Groq 키가 있으면 Groq를 사용하고, Groq 키가 없을 때만 Gemini를 사용합니다. Groq만 강제로 사용하려면 다음처럼 설정합니다.

```env
AI_PROVIDER=groq
```

## Windows 설치 및 실행

PowerShell에서 한 줄씩 실행합니다.

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

## 기존 설치 업데이트

`.env`와 `data`를 백업한 뒤 최신 ZIP을 다시 받습니다. Git으로 설치했다면 다음 명령을 사용합니다.

```bash
git pull
.venv/bin/python -m pip install -e .
```

업데이트 후 버전 확인:

```powershell
python -c "import discord_bot; print(discord_bot.__version__)"
```

정상 버전:

```text
1.5.0
```

## Oracle Cloud 무료 상시 실행

이 봇은 SQLite에 과제·시간표·예약 정보를 저장하므로 영구 디스크가 있는 Oracle Cloud Always Free Ubuntu VM을 권장합니다.

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/smini131-maker/milkway-bot.git
cd milkway-bot
cp .env.example .env
nano .env
bash deploy/install-oracle-cloud.sh
```

상태 확인:

```bash
sudo systemctl status milkway-bot
sudo journalctl -u milkway-bot -f
```

업데이트:

```bash
cd ~/milkway-bot
git pull
.venv/bin/python -m pip install -e .
sudo systemctl restart milkway-bot
```

## AI 동작 확인

Discord에서 순서대로 실행합니다.

```text
/인공지능 사용량
/인공지능 질문
/인공지능 검색
```

`/인공지능 사용량`에는 현재 공급자, 일반 모델, 검색 모델이 표시됩니다.

Groq 기본 검색 모델은 `groq/compound-mini`이며, 사용 불가 시 `groq/compound`로 한 번 자동 교체합니다. 일반 모델도 종료되거나 404가 발생하면 계정에 열린 다른 모델로 자동 재선택합니다.

## 보안

- `.env`, Discord Bot Token, Groq API Key, Gemini API Key, Oracle SSH 개인 키를 GitHub에 올리지 마세요.
- 키가 노출되면 즉시 해당 공급자 콘솔에서 폐기하고 새로 만드세요.
- AI에 학번, 비밀번호, 연락처 같은 민감정보를 입력하지 마세요.

## 테스트

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

## 라이선스

MIT License
