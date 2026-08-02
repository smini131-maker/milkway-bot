# 🌌 Milkway Bot

대학생활 일정, 서버 관리, 무료 질문·검색 기능을 짧은 한글 슬래시 명령어로 사용하는 Discord 봇입니다.

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

## 환경설정

로컬에서는 `.env.example`을 `.env`로 복사해 사용합니다.

```env
DISCORD_TOKEN=Discord_봇_토큰
DEV_GUILD_ID=명령어를_사용할_서버_ID
BOT_DISPLAY_NAME=Milkway Bot
DATABASE_PATH=data/bot.db
LOG_LEVEL=INFO
ENABLE_MEMBER_INTENT=true
ENABLE_MESSAGE_CONTENT_INTENT=true

AI_PROVIDER=groq
GROQ_API_KEY=gsk_실제_키
GROQ_MODEL=auto
GROQ_SEARCH_MODEL=groq/compound-mini
AI_MAX_OUTPUT_TOKENS=1200
AI_DAILY_USER_LIMIT=20
```

`.env`, Discord 토큰, Groq 키는 GitHub나 업로드 ZIP에 넣지 않습니다.

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

## 무료 24시간 실행: Wispbyte

Wispbyte의 무료 Python 서버는 카드 없이 만들 수 있고, 무료 서버를 유지하려면 정기적으로 클라이언트 패널에 로그인해야 합니다. 서버 파일은 보존되므로 `data/bot.db` SQLite 데이터도 재시작 뒤 유지됩니다.

### 1. 안전한 업로드 ZIP 만들기

프로젝트 폴더의 PowerShell에서 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\make-wispbyte-zip.ps1
```

바탕화면에 `milkway-wispbyte.zip`이 생성됩니다. `.env`와 `.venv`는 제외되고 기존 `data/bot.db`는 포함됩니다.

### 2. Wispbyte 서버 만들기

1. Wispbyte Client에 가입하고 이메일을 인증합니다.
2. `Create Server`에서 `Free Plan`을 선택합니다.
3. 런타임은 `Python`을 선택합니다.
4. 서버 이름은 `milkway-bot`으로 지정합니다.
5. 서버 생성 후 `Files`에서 `milkway-wispbyte.zip`을 업로드하고 압축을 풉니다.

### 3. 시작 설정

`Startup`에서 다음을 설정합니다.

```text
Startup Command: python run.py
Main file: run.py
```

`requirements.txt` 자동 설치가 되지 않을 때만 Additional Python Packages에 다음을 입력합니다.

```text
discord.py==2.7.1 python-dotenv tzdata asyncpg groq google-genai
```

### 4. 비밀 환경변수 입력

`Startup → Environment Variables`에 다음 항목을 하나씩 만듭니다.

```text
DISCORD_TOKEN
DEV_GUILD_ID
BOT_DISPLAY_NAME
DATABASE_PATH
LOG_LEVEL
ENABLE_MEMBER_INTENT
ENABLE_MESSAGE_CONTENT_INTENT
AI_PROVIDER
GROQ_API_KEY
GROQ_MODEL
GROQ_SEARCH_MODEL
AI_MAX_OUTPUT_TOKENS
AI_DAILY_USER_LIMIT
```

권장값:

```text
BOT_DISPLAY_NAME=Milkway Bot
DATABASE_PATH=data/bot.db
LOG_LEVEL=INFO
ENABLE_MEMBER_INTENT=true
ENABLE_MESSAGE_CONTENT_INTENT=true
AI_PROVIDER=groq
GROQ_MODEL=auto
GROQ_SEARCH_MODEL=groq/compound-mini
AI_MAX_OUTPUT_TOKENS=1200
AI_DAILY_USER_LIMIT=20
```

`DISCORD_TOKEN`, `DEV_GUILD_ID`, `GROQ_API_KEY`에는 실제 값을 입력합니다.

### 5. 실행 확인

`Console → Start`를 누르고 다음 로그를 확인합니다.

```text
슬래시 명령어 이름 간소화 완료
질문·검색 명령어를 최상위 명령어로 변경 완료
로그인 완료
```

Discord에서 다음 명령을 시험합니다.

```text
/상태
/질문
/검색
```

Wispbyte에서 실행한 뒤에는 같은 토큰의 Windows 봇을 동시에 실행하지 않습니다.

## PostgreSQL 호스팅 지원

`DATABASE_URL` 또는 `POSTGRES_URI`가 설정되면 SQLite 대신 PostgreSQL을 자동 사용합니다. Northflank처럼 무료 데이터베이스를 제공하는 컨테이너 호스팅을 사용할 때 활용할 수 있습니다. 로컬 Windows와 Wispbyte에서는 설정하지 않아도 됩니다.

## 업데이트

GitHub에서 최신 코드를 다시 받거나, Wispbyte의 GitHub Integration에서 `Pull`을 실행한 뒤 서버를 재시작합니다.

현재 버전:

```text
1.5.5
```

## 보안

- `.env`, Discord Bot Token, Groq API Key를 GitHub에 올리지 않습니다.
- 호스팅 패널에는 환경변수로만 토큰과 키를 입력합니다.
- 키가 노출되면 해당 서비스 콘솔에서 즉시 폐기하고 새로 발급합니다.
- 무료 호스팅은 유료 서비스와 동일한 SLA를 보장하지 않으므로 `data/bot.db`를 주기적으로 다운로드해 백업합니다.

## 라이선스

MIT License
