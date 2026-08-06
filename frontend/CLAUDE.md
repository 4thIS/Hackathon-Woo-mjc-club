# frontend — Vue 3 + Vite

## 스택·명령

- Vue 3 (Composition API, `<script setup>`) + Vite + Vue Router + Pinia
- 실행: `npm run dev` (API는 vite proxy로 `:8000`)
- 빌드: `npm run build`

## 구조

```
frontend/src/
  api/index.js     # fetch 래퍼 — 모든 API 호출은 여기로만
  stores/auth.js   # 로그인 상태
  router/index.js
  views/           # 화면 단위 (기획서 §8 화면 목록과 1:1)
  components/
  assets/theme.css # ★ 색·타이포 토큰 — 디자인 시안의 팔레트
```

## 규칙

- API 호출은 반드시 `api/index.js` 를 거친다. 컴포넌트에서 fetch 직접 호출 금지.
- `docs/api.md` 가 계약이다. 응답 형태를 프론트에서 임의로 가공해 다른 형태로 저장하지 않는다.
- 백엔드가 아직 없는 엔드포인트는 `api/index.js` 안에서 mock 응답으로 대체하고 `// MOCK` 주석을 남긴다. 연결되면 mock만 지운다.
- 색·간격은 `theme.css` 토큰만 쓴다. 컴포넌트에 hex 하드코딩 금지.
- 디자인은 `docs/specs/2026-08-06-프론트엔드-디자인-기획.md` 가 기준이다. 확정 페이지(메인·아카이브·상세)는 목업 그대로, 나머지는 §6 제작 규칙을 따른다.
- 백엔드 디렉토리를 수정하지 않는다.
