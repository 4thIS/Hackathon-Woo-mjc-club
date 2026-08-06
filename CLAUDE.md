# Hackathon-Woo-mjc-club — 협업 규칙

명지전문대학 동아리 웹사이트. 2026 RISE사업단 AI 해커톤 (주제 2).
기획: `docs/specs/2026-08-06-동아리웹-기획서.md` · 구현계획: `docs/plans/2026-08-06-구현계획.md`

## 팀

| 이름 | GitHub | 브랜치 | 역할 |
|---|---|---|---|
| 박찬우 | @ssenu | `cw` | **팀장(PM)** — 계약·인프라 승인, 최종 머지 |
| 이우진 | @leemonta9482 | `wj` | 팀원 |
| 김태희 | @kiimth236 | `th` | 팀원 |

전원 풀스택. 작업은 백+프론트를 묶은 **수직 슬라이스(Task)** 단위로 나눈다.
Task 배정과 순서는 구현계획 문서가 기준이다.

## 브랜치·머지

- 각자 자기 브랜치(`wj`/`cw`/`th`)에서 작업 → `main`으로 PR.
- **PR 없이 main 직접 푸시 금지.** 머지는 squash.
- 리뷰: PM이 승인한다. PM 본인 PR은 나머지 중 1명이 승인. 해커톤이므로 리뷰는 "동작 확인 + 계약 위반 없음" 수준으로 빠르게.
- 커밋 메시지: `feat: ...` / `fix: ...` / `docs: ...` 정도만 지키면 됨.

## 계약 (제일 중요한 규칙)

세 파일이 팀의 공유 계약이다. **바꾸려면 PR 전에 PM과 합의**하고, 바꿨으면 PR 제목에 `[계약]`을 붙인다.

| 계약물 | 파일 | 소유 |
|---|---|---|
| API 명세 | `docs/api.md` | 백엔드가 제공하는 형태가 기준. 프론트가 임의 변환하지 않는다 |
| DB 스키마 | `backend/app/models.py` | 컬럼 추가는 자유(additive), 삭제·개명은 합의 필수 |
| 실행 환경 | `docker-compose.yml` | PM |

프론트는 `docs/api.md`만 보고 개발한다. 백엔드가 아직 없으면 **명세대로 mock을 만들어 진행**하고, 붙일 때 mock만 제거한다. 이게 3명이 병렬로 달리는 방법이다.

## 실행

```bash
docker compose up -d db        # Postgres만 도커
cd backend && uv run uvicorn app.main:app --reload   # :8000
cd frontend && npm run dev                            # :5173 (API는 :8000 프록시)
```

전체 도커 실행: `docker compose up --build` (시연 직전 최종 확인용).

## 금지

- 비밀키·API 키를 코드나 커밋에 넣지 않는다. `.env`는 커밋 금지 (`.env.example`만).
- 남의 브랜치에 푸시하지 않는다.
- 계약 파일을 합의 없이 바꾸지 않는다.
- main이 깨진 채로 두지 않는다. 깨졌으면 다른 일보다 먼저 고친다.
