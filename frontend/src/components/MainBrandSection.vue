<script setup>
/* 메인 ② 화면 — 타이틀(경첩) + 브랜드 섹션. 디자인 기획 §5.1 / mockups/main.html 이식.
 * 타이틀 블록은 ②의 첫 요소다. 최상단에선 화면 맨 아래에 걸쳐 보이고,
 * 한 칸 내리면 헤더 밑에 붙는다 — JS 없이 배치로만 해결한다.
 */
import { RouterLink } from 'vue-router'
import logoFull from '../assets/logo-full.png'

const props = defineProps({
  stats: { type: Object, default: null },
})

/* 로딩 중·0이어도 레이아웃이 흔들리지 않게 자리를 고정한다 */
const val = (k) => {
  const v = props.stats?.[k]
  return typeof v === 'number' ? v : '—'
}
</script>

<template>
  <section class="brand" aria-label="서비스 소개">
    <div class="title">
      <h1 class="brand-title">MJC Club Archive</h1>
      <p>mjc hackathon project with Woo</p>
    </div>

    <div class="brand-body">
      <div class="logo-slot">
        <img :src="logoFull" alt="MJC Club Archive" width="720" height="427">
      </div>

      <div class="brand-txt">
        <p class="lead">설명 대신, 지난주에 뭘 했는지.</p>
        <p>동아리 소개글은 어디나 비슷합니다. 그래서 이 아카이브는 소개 대신 <b>활동 기록</b>을 먼저 보여줍니다. 동아리장이 공개한 활동을 넘겨보다가, 마음에 드는 곳에 그 자리에서 가입하세요.</p>
        <p>기록이 쌓이지 않는 이유는 관심이 없어서가 아니라 글 쓰기가 번거롭기 때문입니다. 동아리장이 사진과 한 줄 메모만 올리면 <b>명지전문대학 AI</b>가 활동 글 초안을 만들어 줍니다. 확인하고 고쳐서 올리기만 하면 됩니다.</p>

        <dl class="brand-meta">
          <div><b>{{ val('clubs') }}</b><span>등록 동아리</span></div>
          <div><b>{{ val('recruiting') }}</b><span>모집중</span></div>
          <div><b>{{ val('posts') }}</b><span>활동 기록</span></div>
          <div><b>{{ val('categories') }}</b><span>분야</span></div>
        </dl>

        <div class="go">
          <RouterLink to="/archive">아카이브 바로가기 <i>→</i></RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.brand {
  scroll-snap-align: start;
  scroll-snap-stop: always;      /* 빠르게 튕겨도 이 화면은 건너뛰지 않는다 */
  min-height: calc(100vh - var(--header-h));
}

/* 타이틀 — 두 화면을 잇는 경첩. ①에선 화면 맨 아래, ②에선 맨 위 */
.title {
  height: var(--title-h);
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  text-align: center; padding: 0 20px;
  background: var(--bg);
  box-shadow: 0 10px 24px -18px var(--shadow);
  border-bottom: 1px solid var(--line);
}
.title h1 {
  margin: 0;
  font-size: clamp(30px, 4.6vw, 54px);
  font-weight: 400;
  letter-spacing: -.015em; line-height: 1.1;
}
.title p { margin: 0; font-size: clamp(12px, 1.1vw, 14px); color: var(--dim); letter-spacing: .01em; }

.brand-body {
  min-height: calc(100vh - var(--header-h) - var(--title-h));
  display: grid; grid-template-columns: minmax(280px, 40%) 1fr;
  align-items: center; gap: clamp(28px, 5vw, 72px);
  padding: clamp(32px, 5vh, 64px) clamp(24px, 5vw, 72px) clamp(28px, 4vh, 52px);
}

/* 배경이 투명한 로고다. 판·테두리 없이 그대로 놓는다 */
.logo-slot { justify-self: center; width: min(380px, 86%); line-height: 0; }
.logo-slot img { width: 100%; height: auto; display: block; }

.brand-txt { max-width: 60ch; }
.brand-txt .lead {
  font-size: clamp(17px, 1.9vw, 23px); line-height: 1.55; margin: 0 0 18px;
  font-weight: 700; letter-spacing: -.02em;
}
.brand-txt p { font-size: 14.5px; line-height: 1.85; color: var(--dim); margin: 0 0 14px; }

.brand-meta {
  display: flex; gap: 22px; flex-wrap: wrap;
  margin: 24px 0 0; padding-top: 20px; border-top: 1px solid var(--line);
}
.brand-meta div { min-width: 76px; font-size: 12.5px; color: var(--dim); }
.brand-meta b {
  display: block; min-height: 30px;
  font-size: 21px; color: var(--ink); font-weight: 800;
  letter-spacing: -.02em; font-variant-numeric: tabular-nums; margin-bottom: 2px;
}

.go { margin-top: 28px; display: flex; justify-content: flex-end; }
.go a {
  display: inline-flex; align-items: center; gap: 9px;
  font-size: 15px; font-weight: 700; color: var(--ink);
  padding: 12px 20px; border-radius: 12px;
  border: var(--border); background: var(--card);
}
.go a:hover { border-color: var(--accent); color: var(--accent); }
.go a i { font-style: normal; transition: transform .18s; }
.go a:hover i { transform: translateX(4px); }

@media (max-width: 860px) {
  .brand-body { grid-template-columns: 1fr; gap: 26px; text-align: center; }
  .logo-slot { width: min(300px, 78%); }
  .brand-txt { margin: 0 auto; }
  .brand-meta { justify-content: center; }
  .go { justify-content: center; }
}
</style>
