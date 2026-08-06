# backend — FastAPI + PostgreSQL

## 스택·명령

- Python 3.12 + uv. FastAPI, SQLAlchemy 2, psycopg, bcrypt, httpx, pypdf
- 실행: `uv run uvicorn app.main:app --reload`
- 검사: `uv run ruff check .` · 테스트: `uv run pytest -q`

## 구조

```
backend/app/
  main.py        # 앱 조립, CORS, 정적 서빙
  models.py      # ★ 계약 — SQLAlchemy 모델 (스키마는 create_all, 마이그레이션 도구 없음)
  db.py          # 세션·엔진
  deps.py        # 현재 유저·권한 의존성
  routers/       # auth, clubs, members, posts, admin, ai
  services/      # ai_draft.py (게이트웨이 호출), pdf_text.py, mailer.py
seed.py          # 관리자 계정 + 데모 데이터
```

## 규칙

- `models.py` 는 계약이다. 컬럼 추가는 자유, 삭제·개명은 PM 합의 후.
- 마이그레이션 도구는 안 쓴다. 스키마 바꾸면 `docker compose down -v` 후 재생성 + seed 재실행. (해커톤 한정)
- 권한 검사는 라우터에서 `deps.py` 의존성으로만 한다. 서비스 레이어에서 중복 검사하지 않는다.
- 유저의 AI API 키는 **암호화해서 저장**(Fernet, 키는 `.env`의 `SECRET_KEY`). 응답에는 마지막 4자리만.
- **AI Gateway 호출 시 User-Agent 를 반드시 지정한다.** httpx 기본 UA(`python-httpx/…`)로 나가면
  Cloudflare 가 403(error 1010)으로 막는다. 키 오류로 착각하기 쉽다. 확인된 설정:
  ```python
  httpx.AsyncClient(
      base_url="https://factchat-cloud.mindlogic.ai/v1/gateway",
      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/130.0.0.0 Safari/537.36"},
  )
  ```
  경로 끝 슬래시도 그대로 지킨다: `/models/`, `/chat/completions/`, `/claude/v1/messages/`
- 비전 지원 확인됨 — `chat/completions` 에 `image_url` (base64 data URI) 로 사진을 넘긴다.
  검증에 쓴 모델: `claude-sonnet-5`. 텍스트 전용이면 `gpt-5.6-luna` 도 정상.
- 이메일 발송 실패 시 서버가 죽으면 안 된다. 실패하면 로그 찍고 콘솔에 인증 링크 출력 (시연 폴백).
- 프론트 디렉토리를 수정하지 않는다. API 형태 논의는 `docs/api.md` 로.
