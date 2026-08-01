# 🌌 Milkway Bot

`Milkway Bot`은 Discord 서버 운영 기능과 대학생용 일정·학습 도구, 선택형 **Gemini AI 및 Google 검색** 기능을 한 프로젝트에 묶은 Python 봇입니다. 모든 주요 기능은 슬래시 명령어로 조작하고, 예약·과제·시험·시간표·출석·스터디·사용량 데이터는 SQLite에 저장되어 재시작 후에도 유지됩니다.

## 주요 기능

### 🎓 대학생활

- **과제**: 등록, 마감순 목록, 완료·재개·삭제, 완료 항목 정리
- **시험**: 시험명, 일시, 장소, 메모 관리
- **자동 알림**: 과제와 시험 등록 시 `30m`, `1d`, `1w` 형식으로 사전 리마인더 생성
- **시간표**: 오늘·주간 시간표, 강의실·교수 정보, 시간 충돌 검사
- **출석**: 과목별 출석·지각·결석 누적과 결석률 확인
- **스터디**: 서버 공개 모집, 정원 제한, 참가·탈퇴·멤버 확인·마감
- **대시보드**: 오늘 강의와 가까운 과제·시험을 한 화면에서 확인
- **학점 계산**: 4.5 만점 가중 평균평점, 목표 누적평점에 필요한 향후 평균
- **팀플**: 이름 목록을 무작위로 균형 있게 팀 편성
- **집중 관리**: 포모도로 집중·휴식 리마인더 일괄 등록

### 🤖 Gemini 학습·검색 도우미

`GEMINI_API_KEY`를 설정하면 다음 명령이 활성화됩니다. 키가 없어도 AI를 제외한 기능은 모두 정상 작동합니다.

- 일반 질문과 개념 설명: `/ai ask`
- **최신 정보 Google 검색 및 출처 표시**: `/ai search`
- 강의 노트 핵심·시험대비·발표·회의록 요약: `/ai summarize`
- 현재 채널 최근 대화를 회의록으로 정리: `/ai channel_summary`
- 시험일까지 학습 계획 작성: `/ai study_plan`
- 노트 범위 안에서 복습 퀴즈와 해설 생성: `/ai quiz`
- 공지·이메일·보고서 문장 다듬기: `/ai polish`
- 번역: `/ai translate`
- 공모전·팀플 아이디어 구체화: `/ai brainstorm`
- 모델과 일일 사용량 확인: `/ai usage`

기본 모델은 무료 등급을 지원하는 `gemini-2.5-flash-lite`입니다. `/ai search`는 Gemini의 Google Search grounding을 사용하고, 답변 뒤에 실제 검색 출처 링크를 표시합니다.

Google 공식 가격표 기준으로 Gemini 2.5 Flash와 Flash-Lite의 Google 검색 grounding은 무료 등급에서 두 모델 합산 하루 500회까지 제공됩니다. 무료 한도와 정책은 변경될 수 있으며, 한도를 넘으면 요청이 거절되거나 결제 설정에 따라 비용이 발생할 수 있습니다.

- Gemini API 가격: <https://ai.google.dev/gemini-api/docs/pricing>
- Google 검색 grounding: <https://ai.google.dev/gemini-api/docs/google-search>
- API 키 발급: <https://aistudio.google.com/app/apikey>

### ⏰ 예약과 리마인더

- 원하는 간격, 매일, 매주, 특정 날짜에 메시지 전송
- 예약 조회·중지·재개·수정·삭제·즉시 시험 전송
- 사용자, 역할, `@everyone`, `@here` 맨션
- 개인 상대·절대시각 리마인더와 채널 실패 시 DM 재전송
- 서버별 시간대, 재시작 후 유지, 반복 실패 자동 중지

### 🛡️ 서버 운영

- 일반 메시지, 임베드 공지, 반응 투표
- 환영·퇴장 메시지, 자동 역할, 키워드 자동응답
- 메시지 수정·삭제 및 관리 로그
- 경고, 메시지 청소, 타임아웃, 추방, 차단, 슬로우모드, 채널 잠금
- 사용자와 봇의 대상 채널 권한 이중 검사

## 명령어 요약

| 분류 | 명령어 |
|---|---|
| 대학 대시보드 | `/campus dashboard`, `gpa`, `target_gpa`, `team`, `pomodoro` |
| 과제 | `/assignment add`, `list`, `done`, `reopen`, `delete`, `clear_completed` |
| 시험 | `/exam add`, `list`, `delete` |
| 시간표 | `/timetable add`, `today`, `week`, `delete` |
| 출석 | `/attendance record`, `status`, `reset` |
| 스터디 | `/study create`, `list`, `join`, `leave`, `members`, `close` |
| Gemini | `/ai ask`, `search`, `summarize`, `channel_summary`, `study_plan`, `quiz`, `polish`, `translate`, `brainstorm`, `usage` |
| 예약 | `/schedule interval`, `daily`, `weekly`, `once`, `list`, `pause`, `resume`, `edit`, `time`, `delete`, `run` |
| 리마인더 | `/remind in`, `at`, `list`, `cancel` |
| 메시지 | `/send`, `/announce`, `/poll` |
| 자동화 | `/config ...`, `/autoresponse ...` |
| 관리 | `/mod ...` |
| 기타 | `/도움말`, `/ping`, `/서버정보`, `/유저정보`, `/아바타`, `/선택`, `/주사위`, `/동전`, `/타임스탬프` |

## 설치

### 1. Discord 애플리케이션

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 애플리케이션과 Bot을 만듭니다.
2. Bot Token을 발급합니다. 토큰은 GitHub에 올리지 마세요.
3. 다음 Privileged Gateway Intents를 켭니다.
   - Server Members Intent: 환영 메시지·자동 역할
   - Message Content Intent: 자동응답·메시지 로그
4. OAuth2 설치 범위에서 `bot`, `applications.commands`를 선택합니다.

권장 권한: View Channels, Send Messages, Embed Links, Add Reactions, Read Message History, Manage Messages, Manage Channels, Moderate Members, Kick Members, Ban Members, Manage Roles.

### 2. 실행

#### Windows PowerShell — Git 설치됨

```powershell
git clone https://github.com/smini131-maker/milkway-bot.git
cd milkway-bot
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
Copy-Item .env.example .env
notepad .env
python -m discord_bot
```

#### Windows PowerShell — Git 없음

```powershell
cd $HOME\Desktop
curl.exe -L "https://github.com/smini131-maker/milkway-bot/archive/refs/heads/main.zip" -o "milkway-bot.zip"
Expand-Archive -Path ".\milkway-bot.zip" -DestinationPath "." -Force
Rename-Item ".\milkway-bot-main" "milkway-bot"
cd .\milkway-bot
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
Copy-Item .env.example .env
notepad .env
python -m discord_bot
```

#### Linux / Raspberry Pi

```bash
git clone https://github.com/smini131-maker/milkway-bot.git
cd milkway-bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env
nano .env
python -m discord_bot
```

### 3. 환경변수

최소 설정:

```env
DISCORD_TOKEN=발급받은_봇_토큰
DEV_GUILD_ID=테스트_서버_ID
DATABASE_PATH=data/bot.db
```

Gemini 기능 추가:

```env
GEMINI_API_KEY=Google_AI_Studio에서_발급받은_API_키
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MAX_OUTPUT_TOKENS=1200
AI_DAILY_USER_LIMIT=20
```

- `DEV_GUILD_ID`: 개발 서버에 명령어를 즉시 동기화합니다. 배포 시 비우면 전역 등록됩니다.
- `GEMINI_API_KEY`: Google AI Studio에서 무료로 발급할 수 있습니다.
- `GEMINI_MODEL`: 기본값은 무료 등급과 Google 검색 grounding을 지원하는 `gemini-2.5-flash-lite`입니다.
- `AI_DAILY_USER_LIMIT`: 사용자 1명당 서버별 하루 AI 요청 수입니다.
- `AI_DAILY_USER_LIMIT=0`: 봇 내부 사용자 제한을 해제합니다. Gemini 자체 무료 쿼터와 요청 속도 제한은 해제되지 않습니다.

## 사용 예시

```text
/assignment add course:회로이론 title:5장 연습문제 due:2026-08-10 23:59 remind_before:1d
/exam add course:공업수학 title:중간고사 when:2026-10-20 10:00 location:공학관 301호 remind_before:1w
/timetable add course:기초물리학 weekday:월 start:09:00 end:10:50 location:B201 professor:김교수
/campus dashboard
/campus gpa grades:자료구조=3:A+, 교양=2:B0, 영어=2:A0
/study create title:공업수학 시험대비 description:매주 기출문제 풀이 max_members:6
/ai search query:오늘 발표된 주요 AI 뉴스 알려줘
/ai study_plan subject:회로이론 중간고사 deadline:2026-10-25 daily_minutes:90
/ai quiz material:여기에 강의 노트를 붙여넣기 count:7 difficulty:보통
```

## Docker

```bash
cp .env.example .env
# .env 수정
docker compose up -d --build
docker compose logs -f
```

SQLite는 `./data`에 보존됩니다.

## 테스트

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
```

GitHub Actions는 `main` push와 Pull Request에서 Python 3.11·3.12로 검사합니다.

## 24시간 운영

봇은 실행 중인 PC·Raspberry Pi·서버가 꺼지면 작동하지 않습니다. Linux 상시 실행은 `deploy/milkway-bot.service.example`을 참고하세요.

## 보안과 개인정보

- `.env`, Discord Token, Gemini API Key를 커밋하지 마세요.
- 키가 노출되면 Google AI Studio에서 즉시 폐기하고 새로 발급하세요.
- 봇에게 Administrator 대신 필요한 권한만 부여하세요.
- `/ai channel_summary`는 명령을 실행한 채널의 최근 텍스트를 Gemini API로 전송합니다.
- `/ai search`는 질문을 Gemini API와 Google 검색 grounding에 전송합니다.
- Gemini 무료 등급에 전송된 데이터는 Google 제품 개선에 사용될 수 있습니다. 민감한 수업 자료나 개인정보를 입력하지 마세요.
- 민감정보, 학번, 비밀번호, 개인 연락처를 AI 명령에 입력하지 마세요.
- AI와 검색 답변은 오류가 있을 수 있으므로 과제 제출 전 출처를 직접 확인하세요.
- `data/bot.db`를 정기적으로 백업하세요.

## 변경 내역

[CHANGELOG.md](CHANGELOG.md)에서 Gemini 전환과 Google 검색 패치를 확인할 수 있습니다.

## 라이선스

MIT License
