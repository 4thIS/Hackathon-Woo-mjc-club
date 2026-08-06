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
- [협업 규칙](CLAUDE.md)

## 실행

```bash
cp .env.example .env          # 값 채우기
docker compose up --build     # 전체 실행
```

개발 모드는 [CLAUDE.md](CLAUDE.md#실행) 참고.

## 기술 스택

FastAPI · Vue 3 + Vite · PostgreSQL 16 · Docker · 명지전문대학 AI Gateway
