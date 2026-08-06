<script setup>
/* 메인 ② 화면 — 타이틀(경첩) + 브랜드 섹션. 디자인 기획 §5.1 / mockups/main.html 이식.
 * 타이틀 블록은 ②의 첫 요소다. 최상단에선 화면 맨 아래에 걸쳐 보이고,
 * 한 칸 내리면 헤더 밑에 붙는다 — JS 없이 배치로만 해결한다.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
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

/* ── 스크롤 등장 ──
 * 타임라인과 같은 방식이다(ClubTimeline). 스냅 스크롤이라 관찰자가 한 번만 울리므로,
 * 처음부터 화면에 있는 요소는 마운트 직후 직접 훑어서 드러낸다. */
const root = ref(null)
const reduced =
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
let io = null

onMounted(() => {
  if (reduced || !root.value) return
  const els = [...root.value.querySelectorAll('.rv')]
  io = new IntersectionObserver(
    (es) => es.forEach((e) => {
      if (!e.isIntersecting) return
      e.target.classList.add('in')
      io.unobserve(e.target)
    }),
    { rootMargin: '0px 0px -8% 0px', threshold: 0.06 },
  )
  els.forEach((el) => io.observe(el))
})

onBeforeUnmount(() => io?.disconnect())
</script>

<template>
  <section ref="root" class="brand" aria-label="서비스 소개">
    <div class="title">
      <h1 class="brand-title latin">MJC Club Archive</h1>
      <p class="latin">mjc hackathon project with Woo</p>
    </div>

    <!-- 타이틀 아래 경계선. 첫 화면(캐러셀)에선 화면 밖이라 보이지 않다가,
         두 번째 화면으로 넘어오면 가운데에서 양옆으로 늘어난다 -->
    <div class="rule-wrap"><span class="rule rv"></span></div>

    <div class="brand-body">
      <div class="logo-slot rv">
        <!-- 원본을 자르거나 줄이지 않고 그대로 쓴다 (사용자 지정) -->
        <img :src="logoFull" alt="MJC Club Archive" width="2048" height="2076">
      </div>

      <div class="brand-txt">
        <p class="lead rv">한눈에 보이는 동아리 아카이브와 모집을 AI로</p>

        <dl class="points">
          <div class="rv">
            <dt>흩어진 기록을 한곳에</dt>
            <dd>학교 이메일로 가입하면 교내 동아리의 모집 현황과 활동이 한 화면에 모입니다. 기수·부원 관리도 여기서 합니다.</dd>
          </div>
          <div class="rv">
            <dt>기록은 AI가 도와줍니다</dt>
            <dd>사진과 한 줄 메모만 올리면 <b>명지전문대학 AI</b>가 활동 글 초안을 씁니다. 동아리장은 확인하고 고쳐서 올리기만 하면 됩니다.</dd>
          </div>
          <div class="rv">
            <dt>취향에 맞는 동아리를 <span class="latin">AI Pick!</span></dt>
            <dd>간단한 설문으로 자신에게 알맞은 동아리를 AI가 아카이브를 보고 추천해줍니다. 클릭 몇 번으로 한 학기를 완성하세요.</dd>
          </div>
        </dl>

        <dl class="brand-meta rv">
          <div><b>{{ val('clubs') }}</b><span>등록 동아리</span></div>
          <div><b>{{ val('recruiting') }}</b><span>모집중</span></div>
          <div><b>{{ val('posts') }}</b><span>활동 기록</span></div>
          <div><b>{{ val('categories') }}</b><span>분야</span></div>
        </dl>

        <div class="go rv">
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

/* 타이틀 — 두 화면을 잇는 경첩. ①에선 화면 맨 아래, ②에선 맨 위.
   블록 높이는 그대로 두고 글자만 위로 올린다 (아래 여백이 경첩 역할을 한다) */
.title {
  height: var(--title-h);
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  padding: 0 20px clamp(18px, 4vh, 40px);
  text-align: center;
  background: var(--bg);
}
.title h1 {
  margin: 0;
  font-size: clamp(30px, 4.6vw, 54px);
  font-weight: 400;
  letter-spacing: -.015em; line-height: 1.1;
}
.title p { margin: 0; font-size: clamp(12px, 1.1vw, 14px); color: var(--dim); letter-spacing: .01em; }

/* 두 열 묶음을 화면 가운데에 세운다. 열 폭을 고정하지 않으면 글 폭이 짧은 만큼
   오른쪽이 비어 전체가 왼쪽으로 쏠려 보인다 */
/* 선은 타이틀 블록 바깥(아래)에 둔다 — 첫 화면에서 타이틀만 걸쳐 보이고 선은 안 보인다 */
.rule-wrap { display: flex; justify-content: center; padding: 0 clamp(24px, 5vw, 72px); }
.rule {
  display: block; width: min(1100px, 100%); height: 1px;
  background: linear-gradient(90deg, transparent, var(--line) 12%, var(--line) 88%, transparent);
}

.brand-body {
  min-height: calc(100vh - var(--header-h) - var(--title-h) - 1px);
  display: grid;
  grid-template-columns: minmax(260px, 470px) minmax(0, 620px);
  justify-content: center;
  align-items: center; gap: clamp(28px, 4vw, 64px);
  padding: clamp(32px, 5vh, 64px) clamp(24px, 5vw, 72px) clamp(28px, 4vh, 52px);
}

/* 배경이 투명한 로고다. 판·테두리 없이 그대로 놓는다.
   원본이 정사각이라 위아래 여백이 넓다 — 마크가 이전만큼 보이도록 폭을 키운다 */
.logo-slot { justify-self: center; width: min(480px, 100%); line-height: 0; }
/* 원본 그대로 놓는다 — 위치를 옮기지 않는다 */
.logo-slot img { width: 100%; height: auto; display: block; }

.brand-txt { max-width: none; }
.brand-txt .lead {
  font-size: clamp(19px, 2.1vw, 26px); line-height: 1.5; margin: 0 0 22px;
  font-weight: 700; letter-spacing: -.025em;
}

/* 한 덩어리 문단보다 제목이 붙은 세 항목이 훑기 쉽다 */
.points { margin: 0; display: flex; flex-direction: column; gap: 16px; }
.points dt {
  font-size: 14.5px; font-weight: 700; letter-spacing: -.015em;
  padding-left: 13px; position: relative;
}
.points dt::before {
  content: ""; position: absolute; left: 0; top: .62em;
  width: 5px; height: 5px; border-radius: 50%; background: var(--accent);
}
.points dd {
  margin: 3px 0 0 13px;
  font-size: 13.5px; line-height: 1.8; color: var(--dim);
}

.brand-meta {
  display: flex; gap: 22px; flex-wrap: wrap;
  margin: 26px 0 0; padding-top: 20px; border-top: 1px solid var(--line);
}
.brand-meta div { min-width: 76px; font-size: 12.5px; color: var(--dim); }
.brand-meta b {
  display: block; min-height: 30px;
  font-size: 21px; color: var(--ink); font-weight: 800;
  letter-spacing: -.02em; font-variant-numeric: tabular-nums; margin-bottom: 2px;
}

.go { margin-top: 26px; display: flex; justify-content: flex-end; }
.go a {
  display: inline-flex; align-items: center; gap: 9px;
  font-size: 15px; font-weight: 700; color: var(--ink);
  padding: 12px 20px; border-radius: 12px;
  border: var(--border); background: var(--card);
}
.go a:hover { border-color: var(--accent); color: var(--accent); }
.go a i { font-style: normal; transition: transform .18s; }
.go a:hover i { transform: translateX(4px); }

/* 등장 — 타임라인과 같은 결(흐릿함이 풀리며 올라온다). 순서대로 조금씩 늦춘다 */
.rv {
  opacity: 0; filter: blur(6px); transform: translateY(20px);
  transition: opacity .6s ease, filter .6s ease, transform .6s cubic-bezier(.19,.72,.28,1);
}
.rv.in { opacity: 1; filter: none; transform: none; }
/* 선은 다른 요소와 달리 가운데에서 양옆으로 늘어난다 (.rv 의 transform 을 덮는다) */
/* 스냅 스크롤이 끝나기 전에 다 자라 버리면 늘어나는 게 안 보인다 —
   화면이 멈춘 뒤(.28s) 천천히(2.2s) 뻗는다 */
.rule {
  opacity: 0; filter: none; transform: scaleX(0); transform-origin: center;
  transition: opacity .5s ease .28s, transform 1.9s cubic-bezier(.65,0,.35,1) .28s;
}
.rule.in { opacity: 1; transform: scaleX(1); }

.points div:nth-child(2) { transition-delay: .07s; }
.points div:nth-child(3) { transition-delay: .14s; }
.brand-meta { transition-delay: .1s; }

@media (max-width: 860px) {
  .brand-body { grid-template-columns: 1fr; gap: 26px; text-align: center; }
  .logo-slot { width: min(300px, 78%); }
  .brand-txt { margin: 0 auto; }
  .points { text-align: left; }
  .brand-meta { justify-content: center; }
  .go { justify-content: center; }
}

@media (prefers-reduced-motion: reduce) {
  .rv { opacity: 1; filter: none; transform: none; }
}
</style>
