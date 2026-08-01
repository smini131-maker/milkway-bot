# 🌌 Milkway Bot

대학생활 일정, 간단한 서버 관리, Gemini 질문·검색을 한글 슬래시 명령어로 사용하는 Discord 봇입니다.

## 정식 초대 링크

[Milkway Bot을 Discord 서버에 초대하기](https://discord.com/oauth2/authorize?client_id=1533024340155699290&permissions=1374658194518&integration_type=0&scope=bot%20applications.commands)

- Discord에서 **서버 관리** 권한이 있는 계정으로 링크를 열어야 서버를 선택할 수 있습니다.
- 초대 후 봇 프로그램을 호스팅 서버에서 실행해야 온라인으로 표시됩니다.
- Discord 안에서도 `/초대` 명령으로 같은 링크를 확인할 수 있습니다.

## 봇 이름과 역할 표시를 `은하`로 맞추기

사진처럼 봇 프로필의 전용 역할 이름까지 `은하`로 보이게 하려면 Discord Developer Portal에서 해당 애플리케이션을 연 뒤 다음 두 곳을 변경하세요.

1. `General Information → Name`: `은하`
2. `Bot → Username`: `은하`

코드도 `.env`의 아래 설정을 읽어 시작할 때 봇 사용자명과 서버 별명을 `은하`로 맞춥니다.

```env
BOT_DISPLAY_NAME=은하
```

Discord가 사용자명 변경을 제한하거나 즉시 반영하지 않는 경우에는 Developer Portal의 `Bot → Username`에서 직접 저장한 뒤 봇을 재시작하세요. 일반 서버 역할인 `관리자`를 임의로 이름 변경하지는 않습니다.

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

## 권장 무료 호스팅: Oracle Cloud Always Free

이 봇은 SQLite에 과제·시간표·예약 정보를 저장하므로, 일정 시간 후 꺼지거나 로컬 파일이 사라지는 무료 웹 호스팅보다 **Oracle Cloud Always Free Ubuntu VM**이 적합합니다.

Oracle 계정 등록과 VM 생성은 사용자가 직접 해야 합니다. 저장소에는 Oracle Ubuntu VM에서 자동 실행되도록 설치하는 스크립트가 포함되어 있습니다.

### 1. Oracle Cloud 계정 및 VM 생성

1. Oracle Cloud Free Tier 계정을 만듭니다.
2. 홈 리전을 선택합니다. Always Free 컴퓨트는 홈 리전에서 생성해야 합니다.
3. `Compute → Instances → Create instance`로 이동합니다.
4. 이미지로 Ubuntu를 선택합니다.
5. Shape는 `Always Free eligible`이 표시되는 `VM.Standard.A1.Flex` 또는 사용 가능한 Always Free Shape를 선택합니다.
6. SSH 키를 생성해 개인 키를 안전하게 저장합니다.
7. Public IPv4가 할당된 상태로 VM을 생성합니다.

Discord 봇은 외부에서 들어오는 웹 포트를 열 필요가 없습니다. Discord로 나가는 연결과 SSH 접속만 있으면 됩니다.

### 2. Windows PowerShell에서 Oracle VM 접속

Oracle에서 받은 개인 키 파일과 VM의 공인 IP를 사용합니다.

```powershell
ssh -i "C:\키파일\ssh-key.key" ubuntu@공인_IP
```

Ubuntu 이미지의 기본 접속 계정은 `ubuntu`입니다.

### 3. Oracle VM에 봇 설치

SSH 접속 후 아래 명령을 한 줄씩 실행합니다.

```bash
sudo apt-get update
sudo apt-get install -y git

git clone https://github.com/smini131-maker/milkway-bot.git
cd milkway-bot
cp .env.example .env
nano .env
```

`.env` 예시:

```env
DISCORD_TOKEN=Discord_봇_토큰
DEV_GUILD_ID=명령어를_쓸_서버_ID
BOT_DISPLAY_NAME=은하

DATABASE_PATH=data/bot.db
LOG_LEVEL=INFO
ENABLE_MEMBER_INTENT=true
ENABLE_MESSAGE_CONTENT_INTENT=true

GEMINI_API_KEY=Google_AI_Studio_API_키
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MAX_OUTPUT_TOKENS=1200
AI_DAILY_USER_LIMIT=0
```

저장 후 설치 스크립트를 실행합니다.

```bash
bash deploy/install-oracle-cloud.sh
```

이 스크립트는 Python 가상환경과 패키지를 설치하고, `systemd`에 봇을 등록해 VM 부팅 시 자동 실행 및 오류 발생 시 자동 재시작하도록 설정합니다.

### 4. 실행 상태 확인

```bash
sudo systemctl status milkway-bot
sudo journalctl -u milkway-bot -f
```

재시작:

```bash
sudo systemctl restart milkway-bot
```

업데이트:

```bash
cd ~/milkway-bot
git pull
.venv/bin/python -m pip install -e .
sudo systemctl restart milkway-bot
```

Oracle VM이 실행 중인 동안 Windows 노트북을 꺼도 봇은 온라인 상태를 유지합니다.

## Windows에서 먼저 시험 실행

Git이 설치되어 있지 않아도 ZIP으로 시험할 수 있습니다.

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

Windows가 종료되거나 절전 상태가 되면 이 방식의 봇도 오프라인이 됩니다. 실제 상시 운영은 Oracle Cloud 배포를 사용하세요.

## 시간표 사용 예시

```text
/시간표 추가 과목:회로이론 요일:월 시작:09:00 종료:10:50 강의실:B201 교수:김교수
/시간표 오늘
/시간표 보기
/시간표 삭제 번호:3
```

## Gemini 검색

Google AI Studio에서 무료 API 키를 만든 뒤 `.env`의 `GEMINI_API_KEY`에 넣습니다.

```text
/인공지능 검색 검색어:부산 이번 주말 축제 알려줘 공개:false
```

`AI_DAILY_USER_LIMIT=0`은 봇 내부 제한만 해제합니다. Gemini 무료 등급 자체의 분당·일일 제한은 유지됩니다.

## 명령어가 영어로 보일 때

1. `.env`의 `DEV_GUILD_ID`에 현재 Discord 서버 ID를 입력합니다.
2. 봇을 완전히 종료했다가 다시 실행합니다.
3. Discord를 새로고침합니다.

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
