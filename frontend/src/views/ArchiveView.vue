<script setup>
/**
 * 아카이브 — 디자인 기획 §5.2 확정 화면 (mockups/archive.html 이식)
 *
 * 확정 수치는 그대로 지킨다:
 *   --colw 248px · 36px 베이스라인 그리드 · 우측 3열 grid(컬럼 흘리기 아님)
 * 검색·분야·모집 필터는 전부 클라이언트 계산이다 (docs/api.md §3 — 전체를 한 번에 받는다).
 */
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { useAuth } from '../stores/auth'
import { CATEGORY_NAMES, catKey } from '../components/ClubCategory'
import ClubApplyDialog from '../components/ClubApplyDialog.vue'

/* 카테고리 순서 = 화면에 흐르는 순서. 색은 theme.css 의 카테고리 색 토큰만 쓴다 */
const CATS = CATEGORY_NAMES.map((nm) => ({ nm, v: `var(--cat-${catKey(nm)}-b)` }))

const route = useRoute()
const router = useRouter()
const auth = useAuth()

const clubs = ref([])
const loading = ref(true)
const error = ref('')

/* 개설 신청은 모달이다 (디자인 기획 §6-2). 로그인해야 신청할 수 있으므로
   비로그인이면 버튼을 잠그고 이유를 호버로 알린다 (동아리 가입 신청과 같은 규칙) */
const applyDlg = ref(null)
const applyLocked = computed(() => !auth.isLoggedIn)
const applyReason = computed(() => (applyLocked.value ? '로그인하면 동아리를 개설할 수 있습니다.' : ''))

function openApply() {
  if (applyLocked.value) return
  applyDlg.value?.open()
}

/* /clubs/new 로 들어오면 이 화면으로 보내고 모달을 연다 (라우터 redirect) */
function openFromQuery() {
  if (route.query.new === undefined) return
  const { new: _n, ...rest } = route.query
  router.replace({ path: route.path, query: rest })
  if (!applyLocked.value) nextTick(() => applyDlg.value?.open())
}
watch(() => route.query.new, openFromQuery)

const fCat = ref('전체')
const fRec = ref('all')
const q = ref('')
const qInput = ref(null)

/* 모집중·상시모집은 "모집" 쪽으로 묶는다 (api.md §0.2 recruit_status 3값) */
const isOpen = (c) => c.recruit_status === '모집중' || c.recruit_status === '상시모집'

onMounted(async () => {
  openFromQuery()
  try {
    const res = await api.clubs.list()
    clubs.value = res?.items ?? []
  } catch (e) {
    error.value = e?.message ?? '동아리 목록을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
})

const catCounts = computed(() => {
  const m = Object.create(null)
  for (const c of clubs.value) m[c.category] = (m[c.category] ?? 0) + 1
  return m
})
const openCount = computed(() => clubs.value.filter(isOpen).length)
const closedCount = computed(() => clubs.value.length - openCount.value)

const hit = computed(() => {
  const needle = q.value.trim().toLowerCase()
  return clubs.value.filter(
    (c) =>
      (fCat.value === '전체' || c.category === fCat.value) &&
      (fRec.value === 'all' || (fRec.value === 'open' ? isOpen(c) : !isOpen(c))) &&
      (!needle || (c.name ?? '').toLowerCase().includes(needle)),
  )
})

const groups = computed(() =>
  CATS.map((cat) => ({ ...cat, list: hit.value.filter((c) => c.category === cat.nm) })).filter(
    (g) => g.list.length,
  ),
)

/* 애니메이션 재생 기준. 검색어는 빼둔다 (타이핑마다 다시 재생되면 산만하다) */
const viewKey = computed(() => `${fCat.value}|${fRec.value}`)

const untouched = computed(() => fCat.value === '전체' && fRec.value === 'all' && !q.value.trim())
const sub = computed(() =>
  untouched.value ? `${clubs.value.length}개 동아리` : `${hit.value.length}개 찾음`,
)

/* 매칭 글자 강조 — 색+굵기로만 한다. mark 배경은 쓰지 않는다 (한글이 벌어진다) */
function parts(name) {
  const nm = name ?? ''
  const needle = q.value.trim()
  if (!needle) return [{ t: nm, on: false }]
  const lower = nm.toLowerCase()
  const low = needle.toLowerCase()
  const out = []
  let i = 0
  for (;;) {
    const at = lower.indexOf(low, i)
    if (at < 0) break
    if (at > i) out.push({ t: nm.slice(i, at), on: false })
    out.push({ t: nm.slice(at, at + needle.length), on: true })
    i = at + needle.length
  }
  if (i < nm.length) out.push({ t: nm.slice(i), on: false })
  return out
}

async function clearQuery() {
  q.value = ''
  await nextTick()
  qInput.value?.focus()
}
</script>

<template>
  <div class="wrap">
    <aside class="rail">
      <h1 class="latin">Archive</h1>
      <div class="head-row">
        <p class="sub">{{ loading ? '불러오는 중…' : sub }}</p>
        <!-- 헤더에 있던 진입점. 동아리를 찾다가 없을 때 누르는 자리라 여기가 맞다.
             잠긴 버튼은 마우스 이벤트를 받지 않으므로 감싼 칸이 호버를 대신 받는다 -->
        <span class="apply-slot" :data-tip="applyReason">
          <button class="new-club" type="button" :disabled="applyLocked" @click="openApply">
            <span aria-hidden="true">＋</span> 동아리 개설
          </button>
        </span>
      </div>

      <div class="search">
        <input
          ref="qInput"
          v-model="q"
          type="search"
          placeholder="동아리 이름으로 찾기"
          autocomplete="off"
          aria-label="동아리 이름으로 찾기" />
        <button v-show="q" class="x" type="button" aria-label="검색어 지우기" @click="clearQuery">
          ×
        </button>
      </div>

      <p class="k">분야</p>
      <div class="facet">
        <button type="button" :aria-pressed="fCat === '전체'" @click="fCat = '전체'">
          전체 <b>{{ clubs.length }}</b>
        </button>
        <button
          v-for="c in CATS"
          :key="c.nm"
          type="button"
          :aria-pressed="fCat === c.nm"
          @click="fCat = c.nm">
          <i :style="{ background: c.v }"></i>{{ c.nm }} <b>{{ catCounts[c.nm] ?? 0 }}</b>
        </button>
      </div>

      <p class="k">모집</p>
      <div class="facet">
        <button type="button" :aria-pressed="fRec === 'all'" @click="fRec = 'all'">
          전체 <b>{{ clubs.length }}</b>
        </button>
        <button type="button" :aria-pressed="fRec === 'open'" @click="fRec = 'open'">
          모집중 <b>{{ openCount }}</b>
        </button>
        <button type="button" :aria-pressed="fRec === 'closed'" @click="fRec = 'closed'">
          모집마감 <b>{{ closedCount }}</b>
        </button>
      </div>

      <p class="legend"><span class="dot"></span> 지금 부원을 모집하는 동아리</p>
    </aside>

    <div class="index">
      <p v-if="loading" class="none">불러오는 중…</p>

      <p v-else-if="error" class="warn">{{ error }}</p>

      <p v-else-if="!groups.length" class="none">
        <b>찾는 동아리가 없어요</b>
        검색어나 분야를 바꿔보세요.<br />
        원하는 동아리가 없다면
        <button class="link as-text" type="button" :disabled="applyLocked" @click="openApply">
          직접 개설
        </button>할 수도 있습니다.
      </p>

      <template v-else>
        <section v-for="(g, i) in groups" :key="`${viewKey}-${g.nm}`"
                 class="group" :style="{ '--i': i }">
          <h2><i :style="{ background: g.v }"></i>{{ g.nm }}</h2>
          <ul>
            <li v-for="c in g.list" :key="c.id">
              <RouterLink :to="`/clubs/${c.id}`" :title="c.name">
                <span class="dot" :class="{ off: !isOpen(c) }"></span>
                <span class="nm"
                  ><span v-for="(p, i) in parts(c.name)" :key="i" :class="{ hit: p.on }">{{
                    p.t
                  }}</span></span
                >
                <em>{{ c.member_count }}명</em>
              </RouterLink>
            </li>
          </ul>
        </section>
      </template>
    </div>

    <ClubApplyDialog ref="applyDlg" />
  </div>
</template>

<style scoped>
:focus-visible {
  outline: 2.5px solid var(--accent);
  outline-offset: 3px;
  border-radius: 8px;
}

.wrap {
  /* --row: 베이스라인 한 칸. 모든 블록 높이를 이 배수로 맞춰 가로줄을 정렬한다
     --colw: 목록 한 덩어리의 폭. 고정해야 세로줄이 맞는다 */
  --row: 36px;
  --colw: 248px;

  display: grid;
  grid-template-columns: minmax(260px, 30%) 1fr;
  gap: clamp(28px, 5vw, 72px);
  padding: clamp(36px, 6vh, 70px) clamp(20px, 4vw, 56px) 70px;
  align-items: start;
}

/* ── 좌측 레일 ── */
/* 레일은 내용을 다 펼친 채로 화면을 따라온다 — 안쪽 스크롤은 두지 않는다
   (스크롤이 생기면 제목이 잘려 보인다) */
.rail {
  position: sticky;
  top: calc(var(--header-h) + 28px);
}
.rail h1 {
  margin: 0 0 6px;
  font-size: clamp(38px, 4.6vw, 62px);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1;
}
/* 제목 바로 아래 — 왼쪽은 개수, 오른쪽은 개설 버튼 */
.head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 30px;
}
.rail .sub {
  margin: 0;
  font-size: 13px;
  color: var(--dim);
}
/* 잠금 이유는 마우스를 올렸을 때만 연하게 (동아리 상세의 가입 신청과 같은 규칙) */
.apply-slot {
  position: relative;
  display: inline-flex;
  flex: none;
}
.apply-slot:not([data-tip=''])::after {
  content: attr(data-tip);
  position: absolute;
  right: 0;
  bottom: calc(100% + 8px);
  transform: translateY(4px);
  padding: 7px 12px;
  border-radius: 10px;
  background: var(--card);
  border: var(--border);
  box-shadow: 0 6px 18px var(--shadow);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--dim);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.apply-slot:not([data-tip='']):hover::after {
  opacity: 0.92;
  transform: none;
}

.new-club {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex: none;
  cursor: pointer;
  padding: 6px 12px;
  border: var(--border);
  border-radius: var(--r-chip);
  background: var(--card);
  color: var(--dim);
  font-size: 12.5px;
  font-weight: 700;
  transition: border-color var(--t-hover), color var(--t-hover);
}
.new-club:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.new-club:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.new-club span {
  font-size: 13px;
  line-height: 1;
}

.search {
  position: relative;
  margin-bottom: 26px;
}
.search input {
  width: 100%;
  border: var(--border);
  background: var(--card);
  color: var(--ink);
  border-radius: var(--r-input);
  padding: 12px 38px 12px 15px;
  font: inherit;
  font-size: 14px;
}
.search input::placeholder {
  color: var(--dim);
}
/* 네이티브 취소 버튼은 커스텀 × 와 겹친다 */
.search input::-webkit-search-cancel-button {
  display: none;
}
.search input:focus {
  border-color: var(--accent);
  outline: none;
}
.search .x {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: none;
  color: var(--dim);
  font: inherit;
  font-size: 16px;
  width: 26px;
  height: 26px;
  border-radius: 7px;
  cursor: pointer;
}
.search .x:hover {
  background: var(--chip);
  color: var(--ink);
}

.rail .k {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--dim);
  margin: 0 0 10px;
}
.facet {
  display: flex;
  flex-direction: column;
  gap: 1px;
  margin-bottom: 26px;
}
.facet button {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  color: var(--ink);
  padding: 8px 11px;
  border-radius: 9px;
  font: inherit;
  font-size: 14px;
  cursor: pointer;
}
.facet button:hover {
  background: var(--chip);
}
.facet button[aria-pressed='true'] {
  background: var(--accent);
  color: var(--onAccent);
  font-weight: 700;
}
.facet button i {
  width: 9px;
  height: 9px;
  border-radius: 3px;
  font-style: normal;
  flex: none;
}
.facet button b {
  margin-left: auto;
  font-weight: 400;
  font-size: 12px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
}
.facet button[aria-pressed='true'] b {
  color: var(--onAccent);
  opacity: 0.72;
}

.legend {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--dim);
  padding-top: 18px;
  border-top: 1px solid var(--line);
}
.legend .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  flex: none;
}

/* ── 우측 인덱스 ──
   흘려보내지 않고 행을 맞춘다 — 한 줄의 그룹들은 같은 높이에서 나란히 시작하고,
   다음 줄은 그 줄에서 가장 긴 그룹 아래에서 다시 나란히 시작한다 */
/* 배경 — 메인 캐러셀과 같은 도트 격자(26px · --band).
   목록은 가는 글씨가 촘촘한 화면이라 위쪽만 남기고 아래로 지운다 */
.index::before {
  content: '';
  position: absolute;
  inset: -18px -24px;
  z-index: -1;
  pointer-events: none;
  background-image: radial-gradient(circle, var(--band) 1px, transparent 1px);
  background-size: 26px 26px;
  opacity: 0.34;
  -webkit-mask-image: linear-gradient(180deg, #000 0%, #000 30%, transparent 85%);
  mask-image: linear-gradient(180deg, #000 0%, #000 30%, transparent 85%);
}

.index {
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  column-gap: clamp(28px, 4vw, 64px);
  row-gap: 0;
  align-items: start;
}

/* 등장 — 메인 브랜드 섹션과 같은 결(흐림이 풀리며 올라온다).
   왼쪽 열부터 차례로 60ms 씩 늦춘다 */
@keyframes group-in {
  from {
    opacity: 0;
    filter: blur(7px);
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    filter: none;
    transform: none;
  }
}
.group {
  animation: group-in 0.62s cubic-bezier(0.19, 0.72, 0.28, 1) both;
  animation-delay: calc(var(--i, 0) * 60ms);
}
@media (prefers-reduced-motion: reduce) {
  .group {
    animation: none;
  }
}

/* 그룹 높이 = 36(제목) + 18 + 36n(항목) + 54(아래) = 108 + 36n → 항상 --row 의 배수.
   덕분에 두 번째 줄도 36px 격자 위에서 시작한다 */
.group {
  margin: 0 0 calc(var(--row) * 1.5);
}
.group h2 {
  margin: 0 0 calc(var(--row) / 2);
  height: var(--row);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.02em;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
}
.group h2 i {
  width: 9px;
  height: 9px;
  border-radius: 3px;
  font-style: normal;
}

/* 폭을 고정하고 가운데 정렬 — 컬럼이 넓어져도 세로줄은 그대로 */
.group ul {
  margin: 0 auto;
  padding: 0;
  list-style: none;
  width: 100%;
  max-width: var(--colw);
}
.group li {
  margin: 0;
}
.group a {
  display: flex;
  align-items: center;
  gap: 9px;
  text-decoration: none;
  color: var(--ink);
  font-size: 14px;
  height: var(--row);
  padding: 0 10px;
  border-radius: 8px;
}
.group a:hover {
  background: var(--chip);
  color: var(--accent);
}
.group a .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  flex: none;
}
.group a .dot.off {
  background: transparent;
  border: 1.5px solid var(--line);
}
.group a .nm {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.group a em {
  font-style: normal;
  flex: none;
  width: 34px;
  text-align: right;
  font-size: 11.5px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
  opacity: 0;
  transition: opacity 0.14s;
}
.group a:hover em {
  opacity: 1;
}
/* 한글은 단어 중간이 걸리므로 패딩을 주면 글자가 벌어진다. 색으로만 강조한다 */
.nm .hit {
  color: var(--accent);
  font-weight: 800;
}

.none,
.warn {
  grid-column: 1 / -1;
}
.none {
  color: var(--dim);
  font-size: 14px;
  line-height: 1.8;
}
.none b {
  display: block;
  color: var(--ink);
  font-size: 16px;
  margin-bottom: 6px;
}
.none .link {
  color: var(--accent);
  font-weight: 700;
}
/* 본문 속 링크처럼 보이는 버튼 (모달을 여는 자리) */
.link.as-text {
  border: none;
  background: none;
  padding: 0;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.link.as-text:hover:not(:disabled) {
  text-decoration: underline;
}
.link.as-text:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (prefers-reduced-motion: reduce) {
  .group a em {
    transition: none;
  }
}

@media (max-width: 1180px) {
  .index {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 820px) {
  .wrap {
    grid-template-columns: 1fr;
    gap: 30px;
  }
  .rail {
    position: static;
  }
  .index {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 560px) {
  .index {
    grid-template-columns: 1fr;
  }
}
</style>
