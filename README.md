# 🌌 Milkway Bot

대학생활 일정, 간단한 서버 관리, Gemini 질문·검색을 한글 슬래시 명령어로 사용하는 Discord 봇입니다.

## 정식 초대 링크

[Milkway Bot을 Discord 서버에 초대하기](https://discord.com/oauth2/authorize?client_id=1533024340155699290&permissions=1374658194518&integration_type=0&scope=bot%20applications.commands)

- Discord에서 **서버 관리** 권한이 있는 계정으로 링크를 열어야 서버를 선택할 수 있습니다.
- 초대 후 봇 프로그램을 실행해야 온라인으로 표시됩니다.
- Discord 안에서도 `/초대` 명령으로 같은 링크를 확인할 수 있습니다.

## 간단해진 한글 명령어

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

다음 기능은 단순화를 위해 제거했습니다.

- 스터디 모집·참가 기능
- 출석·지각·결석 기록
- 채널 잠금·잠금 해제
- 예약 중지·재개
- 예약 내용·시간 수정
- 예약 즉시 시험 전송
- 키워드 자동응답
- 복잡한 AI 부가 명령

## Windows 설치

### 1. 최신 코드 내려받기

Git이 설치되어 있지 않아도 됩니다.

```powershell
cd $HOME\Desktop
Remove-Item .\milkway-bot-main -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\milkway-bot.zip -Force -ErrorAction SilentlyContinue
curl.exe -L "https://github.com/smini131-maker/milkway-bot/archive/refs/heads/main.zip" -o "milkway-bot.zip"
Expand-Archive -Path ".\milkway-bot.zip" -DestinationPath "." -Force
cd .\milkway-bot-main
```

### 2. Python 환경 만들기

Python 3.11 이상이 필요합니다. Python 3.13도 사용할 수 있습니다.

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

### 3. 환경변수 설정

```powershell
Copy-Item .env.example .env
notepad .env
```

```env
DISCORD_TOKEN=Discord_봇_토큰
DEV_GUILD_ID=명령어를_쓸_서버_ID

DATABASE_PATH=data/bot.db
LOG_LEVEL=INFO
ENABLE_MEMBER_INTENT=true
ENABLE_MESSAGE_CONTENT_INTENT=true

GEMINI_API_KEY=Google_AI_Studio_API_키
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MAX_OUTPUT_TOKENS=1200
AI_DAILY_USER_LIMIT=0
```

`AI_DAILY_USER_LIMIT=0`은 Milkway Bot 내부의 사용자별 제한을 해제합니다. Gemini 무료 등급 자체의 분당·일일 제한은 그대로 적용됩니다.

### 4. 실행

```powershell
python -m discord_bot
```

Discord에서 다음 순서로 확인합니다.

```text
/핑
/도움말
/시간표 보기
/인공지능 검색
```

## Windows 로그인 시 자동 실행

먼저 수동 실행이 정상 작동하는지 확인한 다음 아래 명령을 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\install-windows-startup.ps1
```

자동 실행 상태 확인:

```powershell
Get-ScheduledTask -TaskName MilkwayBot
```

로그 확인:

```powershell
Get-Content .\data\milkway-bot.log -Wait
```

자동 실행 제거:

```powershell
.\deploy\uninstall-windows-startup.ps1
```

Windows가 종료되거나 절전 상태가 되면 봇도 오프라인이 됩니다. 노트북을 계속 켜 두기 어렵다면 Raspberry Pi 방식이 더 적합합니다.

## Raspberry Pi에서 24시간 실행

```bash
git clone https://github.com/smini131-maker/milkway-bot.git
cd milkway-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
nano .env
bash deploy/install-rpi-service.sh
```

설치 후에는 Raspberry Pi가 부팅될 때 자동으로 실행되고, 오류로 종료되면 자동 재시작합니다.

```bash
sudo systemctl status milkway-bot
sudo journalctl -u milkway-bot -f
sudo systemctl restart milkway-bot
```

## 시간표 사용 예시

강의 등록:

```text
/시간표 추가 과목:회로이론 요일:월 시작:09:00 종료:10:50 강의실:B201 교수:김교수
```

오늘 시간표:

```text
/시간표 오늘
```

전체 시간표:

```text
/시간표 보기
```

삭제할 때는 `/시간표 보기`에 표시되는 번호를 사용합니다.

```text
/시간표 삭제 번호:3
```

## Gemini 검색

Google AI Studio에서 무료 API 키를 만든 뒤 `.env`의 `GEMINI_API_KEY`에 넣습니다.

```text
/인공지능 검색 검색어:부산 이번 주말 축제 알려줘 공개:false
```

검색 답변 뒤에는 Gemini Google Search grounding에서 받은 출처 링크가 함께 표시됩니다.

## 명령어가 영어로 계속 보일 때

1. `.env`의 `DEV_GUILD_ID`에 현재 Discord 서버 ID를 입력합니다.
2. 봇을 완전히 종료했다가 다시 실행합니다.
3. Discord를 새로고침합니다.

개발 서버를 지정한 경우 봇 시작 시 과거 전역 영문 명령어를 정리하고 한글 명령어를 서버에 다시 동기화합니다.

## 보안

- `.env`, Discord Bot Token, Gemini API Key를 GitHub에 올리지 마세요.
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
