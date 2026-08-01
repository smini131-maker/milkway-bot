# Contributing

1. Issue에서 변경 목적을 먼저 설명합니다.
2. 별도 브랜치에서 작업합니다.
3. `pip install -e ".[dev]"`로 개발 의존성을 설치합니다.
4. `ruff check .`와 `pytest`를 통과시킵니다.
5. 토큰, `.env`, 실제 사용자 데이터가 포함되지 않았는지 확인합니다.
6. Pull Request에 변경 내용과 검증 방법을 작성합니다.
