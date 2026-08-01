# 🌌 Milkway Bot

대학생활 일정, 간단한 서버 관리, Gemini 질문·검색을 한글 슬래시 명령어로 사용하는 Discord 봇입니다.

## 정식 초대 링크

[Milkway Bot을 Discord 서버에 초대하기](https://discord.com/oauth2/authorize?client_id=1533024340155699290&permissions=1374658194518&integration_type=0&scope=bot%20applications.commands)

- Discord에서 **서버 관리** 권한이 있는 계정으로 링크를 열어야 서버를 선택할 수 있습니다.
- 초대한 뒤 봇 프로그램을 실행해야 온라인으로 표시됩니다.
- Discord 안에서도 `/초대` 명령으로 같은 링크를 확인할 수 있습니다.

## 봇 표시 이름

기본 권장 이름은 `Milkway Bot`입니다.

```env
BOT_DISPLAY_NAME=Milkway Bot
```

이 값이 있으면 실행할 때 봇 사용자명과 각 서버의 별명을 해당 값으로 맞춥니다. 이름을 코드에서 자동 변경하지 않고 Discord Developer Portal과 서버의 현재 이름을 그대로 유지하려면 아래처럼 비워 두세요.

```env
BOT_DISPLAY_NAME=
```

일반 서버 역할인 `관리자`의 이름은 변경하지 않습니다. Discord가 사용자명 변경을 제한하면 Developer Portal의 `Bot → Username`에서 직접 `Milkway Bot`으로 저장하세요.

## 간단한 한글 명령어

| 분류 | 명령어 |
|---|---|
| 과제 | `/과제 추가`, `/과제 보기`, `/과제 완료`, `/과제 삭제` |
| 시험 | `/시험 추가`, `/시험 보기`, `/시험 삭제` |
| 시간표 | `/시간표 추가`, `/시간표 오늘`, `/시간표 보기`, `/시간표 삭제` |
| 대학생활 | `/대학생 한눈에`, `/대학생 학점`, `/대학생 집중` |
| Gemini | `/인공지능 질문`, `/인공지능 검색`, `/인공지능 요약`, `/인공지능 퀴즈`, `/인공지능 사용량` |
| 개인 알림 | `/알림 후에`, `/알림 날짜`, `/알림 보기`, `/알림 삭제` |
| 자동 메시지 | `/예약 간격`, `/예약 매일`, `/예약 매주`, `/예약 한번`, `/예약 보기`, `/예약 삭제` |
| 메시지 | `/메시지`, `/공지`, `/투표` |
| 서버 설정 | `/설정 시간대`, `/설정 환영`, `/설정 퇴장`, `/설정 자동역할`, `/설정 로그`, `/설정 끄기`, `/설정 보기` |
| 관리 | `/관리 삭제`, `/관리 타임아웃`, `/관리 타임아웃해제`, `/관리 추방`, `/관리 차단`, `/관리 차단해제`, `/관리 슬로우`, `/관리 경고`, `/관리 경고보기`, `/관리 경고삭제` |
| 기타 | `/도움말`, `/초대`, `/핑`, `/서버정보`, `/사용자정보`, `/아바타`, `/선택`, `/주사위`, `/동전`, `/시간` |

제거된 기능:

- 스터디 모집·참가
- 출석·지각·결석 기록
- 채널 잠금·잠금 해제
- 예약 중지·재개·수정·즉시 시험 전송
- 키워드 자동응답
- 복잡한 AI 부가 명령

## Windows에서 시험 실행

Git이 설치되어 있지 않아도 ZIP으로 실행할 수 있습니다.

```powershell
cd $HOME\Desktop
Remove-Item .\milkway-bot-main -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\milkway-bot.zip -Force -ErrorAction SilentlyContinue
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

## 환경설정 예시

```env
DISCORD_TOKEN=Discord_봇_토큰
DEV_GUILD_ID=명령어를_쓸_서버_ID
BOT_DISPLAY_NAME=Milkway Bot

DATABASE_PATH=data/bot.db
LOG_LEVEL=INFO
ENABLE_MEMBER_INTENT=true
ENABLE_MESSAGE_CONTENT_INTENT=true

GEMINI_API_KEY=Google_AI_Studio_API_키
GEMINI_MODEL=auto
GEMINI_MAX_OUTPUT_TOKENS=1200
AI_DAILY_USER_LIMIT=0
```

`GEMINI_MODEL=auto`는 해당 API 키로 실제 사용할 수 있는 최신 일반 Flash 모델을 자동 선택합니다.

## Oracle Cloud 무료 VM 배포

SQLite 데이터를 유지하면서 노트북을 꺼도 봇을 계속 실행하려면 Oracle Cloud Always Free Ubuntu VM을 사용할 수 있습니다.

### 1. VM 생성

1. Oracle Cloud Free Tier 계정을 만듭니다.
2. `Compute → Instances → Create instance`로 이동합니다.
3. Ubuntu와 `Always Free eligible` Shape를 선택합니다.
4. 공인 IPv4를 할당합니다.
5. SSH 개인 키를 내려받아 안전하게 보관합니다.

### 2. Windows에서 접속

```powershell
ssh -i "C:\키파일\ssh-key.key" ubuntu@공인_IP
```

### 3. 설치

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/smini131-maker/milkway-bot.git
cd milkway-bot
cp .env.example .env
nano .env
bash deploy/install-oracle-cloud.sh
```

### 4. 상태와 로그

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

## 시간표 사용 예시

```text
/시간표 추가 과목:회로이론 요일:월 시작:09:00 종료:10:50 강의실:B201 교수:김교수
/시간표 오늘
/시간표 보기
/시간표 삭제 번호:3
```

## Gemini

Google AI Studio에서 API 키를 만든 뒤 `.env`의 `GEMINI_API_KEY`에 넣습니다.

```text
/인공지능 질문 내용:회로이론의 키르히호프 법칙을 설명해줘
/인공지능 사용량
```

`AI_DAILY_USER_LIMIT=0`은 봇 내부 제한만 해제합니다. Google의 무료 등급 제한은 별도로 적용됩니다. Google 검색 연결은 선택된 모델과 프로젝트의 결제 등급에 따라 제한될 수 있습니다.

## 명령어가 영어로 보일 때

1. `.env`의 `DEV_GUILD_ID`에 현재 Discord 서버 ID를 입력합니다.
2. 봇을 완전히 종료했다가 다시 실행합니다.
3. Discord를 `Ctrl + R`로 새로고침합니다.

## 보안

- `.env`, Discord Bot Token, Gemini API Key, Oracle SSH 개인 키를 GitHub에 올리지 마세요.
- 키가 노출되면 즉시 재발급하세요.
- 봇 역할은 자동으로 부여할 역할보다 위에 있어야 합니다.
- Gemini에 학번, 비밀번호, 연락처 같은 민감정보를 입력하지 마세요.

## 테스트

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

## 라이선스

MIT License
