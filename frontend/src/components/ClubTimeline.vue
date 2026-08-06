<script setup>
/* 활동 기록 타임라인 — 디자인 기획 §5.3
 * 가운데 축 / 좌우 번갈아(오른쪽부터) / 오래된 순 / 5건 배치 로드.
 * 확정 수치: --axis 150px, 마디 11px + --bg 4px 링, 등장 0.62s(blur 7px + ↓28px),
 *            IntersectionObserver rootMargin -12%, 바닥 260px 전 다음 배치.
 */
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import api from '../api'
import { catVars, postEmoji } from './ClubCategory'

const props = defineProps({
  clubId: { type: [String, Number], required: true },
  category: { type: String, default: '' },
})

const BATCH = 5

const posts = ref([])
const total = ref(0)
const hasMore = ref(true)
const firstYear = ref(null)
const loading = ref(false)
const failed = ref(false)      // 501 등 — 섹션만 빈 상태로 두고 화면은 살린다
const revealed = ref(new Set())

const reduceMotion =
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

const phVars = computed(() => catVars(props.category))
const remaining = computed(() => Math.max(total.value - posts.value.length, 0))
const countLabel = computed(() =>
  total.value ? `공개된 활동 ${total.value}건 · 오래된 순` : '',
)

const dateText = (d) => (d ? String(d).replaceAll('-', '.') : '')
const isRevealed = (i) => reduceMotion || revealed.value.has(i)

/* ── 등장 관찰자 ── */
let reveal = null
const rowEls = []

function rowRef(el, i) {
  if (!el || reduceMotion || !reveal || el.dataset.observed) return
  el.dataset.observed = '1'
  el.dataset.i = String(i)
  rowEls.push(el)
  reveal.observe(el)
}

/* IntersectionObserver 는 스크롤이 일어나야 울린다. 처음부터 화면 안에 들어 있는 행은
 * 사용자가 스크롤할 때까지 opacity 0 으로 남아 **내용이 통째로 안 보인다.**
 * 배치를 붙일 때마다 직접 훑어서 이미 보이는 행을 드러낸다. (transition 은 그대로 재생된다) */
function sweepReveal() {
  if (reduceMotion || !reveal) return
  for (const el of rowEls) {
    if (!el.isConnected || revealed.value.has(Number(el.dataset.i))) continue
    const r = el.getBoundingClientRect()
    if (r.top < window.innerHeight && r.bottom > 0) {
      revealed.value.add(Number(el.dataset.i))
      reveal.unobserve(el)
    }
  }
}

/* ── 배치 로드 ── */
async function loadMore() {
  if (loading.value || !hasMore.value || failed.value) return
  loading.value = true
  try {
    const r = await api.clubs.posts(props.clubId, { offset: posts.value.length, limit: BATCH })
    posts.value = posts.value.concat(r?.items ?? [])
    total.value = r?.total ?? posts.value.length
    firstYear.value = r?.first_year ?? firstYear.value
    hasMore.value = !!r?.has_more && (r?.items?.length ?? 0) > 0
  } catch {
    // 백엔드 미구현(501)·네트워크 오류 — 타임라인 섹션만 빈 상태
    failed.value = true
    hasMore.value = false
  } finally {
    loading.value = false
  }
  await nextTick()
  sweepReveal()
  maybeFill()
}

/* 바닥 감시자가 이미 화면 안에 있으면 IO 가 다시 안 울린다 — 직접 확인해 이어 채운다 */
const tailEl = ref(null)
let tailIO = null
function maybeFill() {
  if (!hasMore.value || loading.value || !tailEl.value) return
  const r = tailEl.value.getBoundingClientRect()
  if (r.top < window.innerHeight + 260) loadMore()
}

/* 애니메이션을 끈 사용자에겐 전건 즉시 렌더 */
async function loadAll() {
  let guard = 0
  while (hasMore.value && !failed.value && guard++ < 60) await loadMore()
}

onMounted(async () => {
  if (!reduceMotion) {
    reveal = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (!e.isIntersecting) return
          revealed.value.add(Number(e.target.dataset.i))
          reveal.unobserve(e.target)      // 한 번 드러나면 되돌리지 않는다
        })
      },
      { rootMargin: '0px 0px -12% 0px', threshold: 0.08 },
    )
    tailIO = new IntersectionObserver(
      (es) => { if (es[0].isIntersecting) loadMore() },
      { rootMargin: '260px' },            // 바닥에 닿기 전에 미리 채운다
    )
  }

  await loadMore()
  if (reduceMotion) await loadAll()
  await nextTick()
  sweepReveal()
  if (tailIO && tailEl.value) tailIO.observe(tailEl.value)
})

onBeforeUnmount(() => {
  reveal?.disconnect()
  tailIO?.disconnect()
})
</script>

<template>
  <section class="tl-wrap" :style="phVars">
    <div class="tl-head">
      <h2 class="section-title">활동 기록</h2>
      <span class="sub">{{ countLabel }}</span>
    </div>

    <div class="tl">
      <div v-if="failed && !posts.length" class="tl-empty">
        <p>활동 기록은 곧 표시됩니다.</p>
        <p class="sub">잠시 뒤 새로고침해 주세요.</p>
      </div>

      <div v-else-if="!posts.length && !loading" class="tl-empty">
        <p>아직 공개된 활동 기록이 없습니다.</p>
        <p class="sub">동아리장이 첫 기록을 올리면 여기에 쌓입니다.</p>
      </div>

      <div v-for="(p, i) in posts" :key="p.id"
           :ref="(el) => rowRef(el, i)"
           class="tl-row"
           :class="[i % 2 === 0 ? 'r' : 'l', { in: isRevealed(i) }]">
        <!-- DOM 순서는 a · axis · b 로 고정하고, 좌우 배치는 grid-column 으로 바꾼다 -->
        <div class="slot a"></div>

        <div class="slot axis"><span class="node"></span></div>

        <div class="slot b">
          <div class="conn"><span class="date">{{ dateText(p.activity_date) }}</span></div>
          <RouterLink class="post" :to="`/posts/${p.id}`">
            <div class="shot" :style="p.photo ? { backgroundImage: `url(${p.photo})` } : null">
              <span v-if="!p.photo">{{ postEmoji(p.id) }}</span>
            </div>
            <div class="body">
              <h3>
                {{ p.title }}
                <span v-if="p.is_public === false" class="tag private">비공개</span>
              </h3>
              <p>{{ p.excerpt }}</p>
              <div v-if="p.tags?.length" class="tags">
                <span v-for="t in p.tags" :key="t" class="tag">{{ t }}</span>
              </div>
            </div>
          </RouterLink>
        </div>
      </div>

      <div ref="tailEl" class="tail">
        <div v-if="hasMore" class="tl-more">
          <span class="bar"></span><span class="pulse"></span>
          스크롤하면 {{ remaining }}건이 더 나옵니다
        </div>
        <div v-else-if="posts.length" class="tl-end">
          <i></i>여기까지가 공개된 활동입니다<br>
          <template v-if="firstYear">{{ firstYear }}년부터 </template>{{ total }}건
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tl-wrap { --axis: 150px; --gap: 46px; }

.tl-head {
  max-width: 1160px; margin: 0 auto;
  padding: 0 clamp(20px, 4vw, 56px);
  display: flex; align-items: baseline; gap: 12px;
}
.tl-head h2 { margin: 0; }

.tl {
  position: relative; max-width: 1160px; margin: 26px auto 0;
  padding: 10px clamp(20px, 4vw, 56px) 90px;
}

.tl-empty { text-align: center; padding: 30px 0 40px; color: var(--dim); }
.tl-empty p { margin: 0 0 6px; }

/* 세 칸을 모두 1행에 못박는다. grid-row 를 안 주면 왼쪽 행(l)에서 축이
   자동 배치로 밀려 높이 0 인 새 행에 떨어지고, 그 구간만 세로선이 끊긴다. */
.tl-row { display: grid; grid-template-columns: 1fr var(--axis) 1fr; margin-bottom: var(--gap); }
.tl-row .slot { position: relative; min-width: 0; grid-row: 1; }
.tl-row .slot.axis { grid-column: 2; }
.tl-row.r .slot.a { grid-column: 1; }  .tl-row.r .slot.b { grid-column: 3; }
.tl-row.l .slot.b { grid-column: 1; }  .tl-row.l .slot.a { grid-column: 3; }

/* 축을 행마다 한 토막씩 갖게 해서, 행이 나타날 때 선도 함께 자란다 */
.tl-row .slot.axis::before {
  content: ""; position: absolute; left: 50%; top: 0; bottom: calc(var(--gap) * -1);
  width: 2px; background: var(--line); transform: translateX(-1px);
}

/* 등장 — 흐릿한 상태에서 초점이 맞듯 */
.tl-row {
  opacity: 0; filter: blur(7px); transform: translateY(28px);
  transition: opacity .62s ease, filter .62s ease, transform .62s cubic-bezier(.19,.72,.28,1);
}
.tl-row.in { opacity: 1; filter: none; transform: none; }
.tl-row .post { transition: transform .62s cubic-bezier(.19,.72,.28,1) .08s, box-shadow var(--t-hover); }
.tl-row:not(.in) .post { transform: translateY(14px); }

/* 축 위의 마디 */
.node {
  position: absolute; left: 50%; top: 52px; width: 11px; height: 11px; border-radius: 50%;
  background: var(--accent); transform: translate(-50%, -50%);
  box-shadow: 0 0 0 4px var(--bg);
}
/* 축 → 카드 연결선 + 날짜.
   폭은 축 컬럼의 절반이다 — 마디(점)에서 카드 쪽으로만 뻗어야 한다.
   전체 폭을 주면 점 반대편으로도 선이 삐져나온다. */
.conn {
  position: absolute; top: 52px; width: calc(var(--axis) / 2); height: 2px;
  background: var(--accent); opacity: .55;
}
.tl-row.r .conn { left: calc(var(--axis) / -2); }
.tl-row.l .conn { right: calc(var(--axis) / -2); }
.conn::after {
  content: ""; position: absolute; top: 50%; width: 0; height: 0;
  border-top: 5px solid transparent; border-bottom: 5px solid transparent;
}
.tl-row.r .conn::after { right: -1px; transform: translateY(-50%); border-left: 8px solid var(--accent); }
.tl-row.l .conn::after { left: -1px; transform: translateY(-50%); border-right: 8px solid var(--accent); }
.conn .date {
  position: absolute; left: 50%; bottom: 9px; transform: translateX(-50%);
  font-size: 12.5px; font-weight: 700; color: var(--dim); white-space: nowrap;
}

.post {
  display: block; background: var(--card); border: var(--border);
  border-radius: var(--r-card); overflow: hidden; cursor: pointer; color: inherit;
}
.post:hover { box-shadow: 0 14px 34px var(--shadowUp); }
.post .shot {
  height: 190px; background: linear-gradient(150deg, var(--ph-a), var(--ph-b));
  background-size: cover; background-position: center;
  display: grid; place-items: center; font-size: 2.6rem;
}
.post .body { padding: 15px 17px 17px; }
.post h3 { margin: 0 0 8px; font-size: 16px; letter-spacing: -.02em; }
.post p {
  margin: 0; font-size: 13.5px; line-height: 1.75; color: var(--dim);
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.post .tags { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; }

.tag {
  display: inline-block; background: var(--chip); border: 1px solid var(--line);
  border-radius: var(--r-chip); padding: 2px 10px; font-size: 11.5px; color: var(--dim); font-weight: 600;
}
.tag.private { color: var(--warnInk); background: var(--warnBg); border-color: var(--warnLine); vertical-align: middle; }

.tl-more {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  padding: 8px 0 0; color: var(--dim); font-size: 12.5px;
}
.tl-more .bar { width: 2px; height: 52px; background: var(--line); }
.tl-more .pulse {
  width: 11px; height: 11px; border-radius: 50%; background: var(--line);
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse { 0%, 100% { opacity: .35; transform: scale(.85); } 50% { opacity: 1; transform: scale(1.15); } }

.tl-end {
  display: flex; flex-direction: column; align-items: center; gap: 11px;
  padding-top: 6px; color: var(--dim); font-size: 12.5px; text-align: center;
}
.tl-end i { width: 9px; height: 9px; border-radius: 50%; background: var(--line); font-style: normal; }

@media (max-width: 900px) {
  .tl-wrap { --axis: 56px; }
  .tl-row { grid-template-columns: var(--axis) 1fr; }
  .tl-row .slot.axis::before { left: 14px; }
  .tl-row .slot.a { display: none; }
  .tl-row .slot.axis { grid-column: 1; }
  .tl-row.l .slot.b, .tl-row.r .slot.b { grid-column: 2; }
  .tl-row .node { left: 14px; }
  /* 축이 왼쪽 14px 에 있으므로 연결선도 거기서 시작한다 (마디 반대편으로 뻗지 않게) */
  .tl-row.l .conn, .tl-row.r .conn {
    left: calc(14px - var(--axis)); right: auto; width: calc(var(--axis) - 14px);
  }
  .tl-row.l .conn::after { left: auto; right: -1px; border-right: none; border-left: 8px solid var(--accent); }
  .conn .date { left: 0; transform: none; bottom: 8px; font-size: 11.5px; }
}

@media (prefers-reduced-motion: reduce) {
  .tl-row { opacity: 1; filter: none; transform: none; }
  .tl-row:not(.in) .post { transform: none; }
}
</style>
