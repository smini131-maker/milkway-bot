# GitHub 게시 정보

대상 저장소는 다음과 같습니다.

```text
https://github.com/smini131-maker/milkway-bot
```

이 프로젝트의 `main` 브랜치 변경 사항은 해당 저장소에 게시합니다.

로컬에서 다시 연결해야 할 때:

```bash
git remote add origin https://github.com/smini131-maker/milkway-bot.git
git push -u origin main
```

업로드 후 확인:

- Actions 탭에서 Python 3.11·3.12 CI 통과 여부
- `.env`, Discord Token, OpenAI API Key가 커밋되지 않았는지
- 실제 실행 환경의 `.env`에만 비밀 키가 저장되었는지
- `data/bot.db`가 Git에서 제외되는지
