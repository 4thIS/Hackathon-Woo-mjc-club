# 명지전문대학 동아리 웹사이트

2026학년도 RISE사업단 AI 해커톤 경진대회 — 주제 2 (학업·활동·대학생활 도움)

동아리를 찾고 가입할 수 있고, 동아리장은 **사진과 메모만 올리면 명지전문대학 AI가 활동 글 초안을 써주는** 동아리 활동 기록·홍보 웹사이트.

## 팀

| 이름 | 학과 | GitHub | 브랜치 |
|---|---|---|---|
| 박찬우 (팀장) | <!-- 학과 --> | [@ssenu](https://github.com/ssenu) | `cw` |
| 이우진 | <!-- 학과 --> | [@leemonta9482](https://github.com/leemonta9482) | `wj` |
| 김태희 | <!-- 학과 --> | [@kiimth236](https://github.com/kiimth236) | `th` |

## 문서

- [기획서](docs/specs/2026-08-06-동아리웹-기획서.md)
- [구현계획](docs/plans/2026-08-06-구현계획.md)
- [**API 명세**](docs/api.md) ← 백엔드·프론트 공통 계약. 개발 전에 읽는다
- [프론트엔드 디자인 기획](docs/specs/2026-08-06-프론트엔드-디자인-기획.md) · 목업 `mockups/`
- [협업 규칙](CLAUDE.md)

## 실행

### 개발 (권장) — Postgres만 도커, 앱은 로컬에서 --reload

```bash
cp .env.example .env
docker compose up -d db

cd backend
uv sync
uv run python seed.py                                  # 데모 데이터
uv run uvicorn app.main:app --reload                   # :8000  (문서 /api/docs)

cd ../frontend
npm install
npm run dev                                            # :5173  (API는 :8000 프록시)
```

### 전체 도커 (시연 직전 확인용)

```bash
docker compose up --build       # 프론트 :8080 · API :8000
```

### 데모 계정 (seed)

| 계정 | 이메일 | 비밀번호 |
|---|---|---|
| 학생 | `26011234@mjc.ac.kr` | `test1234` |
| 동아리장 | `24010001@mjc.ac.kr` | `test1234` |
| 관리자 | `00000000@mjc.ac.kr` | `test1234` |

스키마를 바꿨으면 `docker compose down -v` 후 DB 재생성 + `uv run python seed.py --reset`.
(마이그레이션 도구를 쓰지 않는다 — 구현계획 §7)

## 기술 스택

FastAPI · Vue 3 + Vite · PostgreSQL 16 · Docker · 명지전문대학 AI Gateway
