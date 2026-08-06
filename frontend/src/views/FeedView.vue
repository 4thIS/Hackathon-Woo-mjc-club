<script setup>
/**
 * 전체 피드 — 동아리를 가리지 않고 활동 글을 최신순으로 본다. (api.md §3 GET /posts)
 *
 * 동아리 상세의 타임라인과 일부러 다르게 만든다:
 *   타임라인 = 한 동아리의 역사 → 가운데 축 · 오래된 순
 *   피드     = 지금 무슨 일이 있는지 → 카드 3열 격자 · 최신 순
 * 카드 생김새(사진 190px + 본문 + 태그)는 타임라인과 맞춰 같은 서비스로 읽히게 한다.
 *
 * 검색은 서버가 한다 — 글 전체를 받아두고 거르는 아카이브와 달리 피드는 계속 늘어난다.
 */
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import api from '../api'
import { catVars, postEmoji } from '../components/ClubCategory'

const BATCH = 12

const posts = ref([])
const total = ref(0)
const hasMore = ref(true)
const loading = ref(false)
const error = ref('')
const loaded = ref(false)        // 첫 응답을 받았는가 — 빈 상태와 로딩을 구분한다

const q = ref('')
const qInput = ref(null)
const tailEl = ref(null)

const dateText = (d) => (d ? String(d).replaceAll('-', '.') : '')

const sub = computed(() => {
  if (!loaded.value) return '불러오는 중…'
  if (q.value.trim()) return `${total.value}건 찾음`
  return `공개된 활동 ${total.value}건 · 최신순`
})

async function load({ reset = false } = {}) {
  if (loading.value) return
  if (!reset && !hasMore.value) return

  loading.value = true
  error.value = ''
  const offset = reset ? 0 : posts.value.length
  const needle = q.value.trim()

  try {
    const res = await api.posts.feed({ q: needle, offset, limit: BATCH })
    // 입력이 그새 바뀌었으면 늦게 온 응답을 버린다 (빠르게 타이핑하면 순서가 뒤집힌다)
    if (needle !== q.value.trim()) return
    const items = res?.items ?? []
    posts.value = reset ? items : posts.value.concat(items)
    total.value = res?.total ?? posts.value.length
    hasMore.value = !!res?.has_more
  } catch (e) {
    error.value = e?.message ?? '피드를 불러오지 못했습니다.'
    hasMore.value = false
  } finally {
    loading.value = false
    loaded.value = true
    // 첫 화면이 다 안 찼으면 바닥 관찰자가 울리지 않는다 — 한 번 더 채운다
    await nextTick()
    if (hasMore.value && !error.value && tailInView()) load()
  }
}

/* ── 바닥에 닿으면 다음 배치 ── */
let io = null

function tailInView() {
  const el = tailEl.value
  if (!el) return false
  const r = el.getBoundingClientRect()
  return r.top < window.innerHeight + 260
}

onMounted(() => {
  io = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) load()
    },
    { rootMargin: '260px' },
  )
  if (tailEl.value) io.observe(tailEl.value)
  load({ reset: true })
})

onBeforeUnmount(() => io?.disconnect())

/* 검색 — 타이핑마다 쏘지 않는다 */
let timer = null
watch(q, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    hasMore.value = true
    load({ reset: true })
  }, 280)
})
onBeforeUnmount(() => clearTimeout(timer))

async function clearQuery() {
  q.value = ''
  await nextTick()
  qInput.value?.focus()
}
</script>

<template>
  <div class="wrap">
    <header class="head">
      <div class="head-l">
        <h1 class="latin">Feed</h1>
        <p class="sub">{{ sub }}</p>

        <div class="search">
          <input
            ref="qInput"
            v-model="q"
            type="search"
            placeholder="제목 · 내용 · 동아리 · 태그로 찾기"
            autocomplete="off"
            aria-label="활동 글 검색" />
          <button v-show="q" class="x" type="button" aria-label="검색어 지우기" @click="clearQuery">
            ×
          </button>
        </div>
      </div>

      <p class="head-r sub">
        모든 동아리의 활동을 한 줄로 모았습니다.<br />
        동아리별로 보려면 <RouterLink to="/archive">아카이브</RouterLink>로 가세요.
      </p>
    </header>

    <p v-if="error && !posts.length" class="warn state">{{ error }}</p>

    <p v-else-if="loaded && !posts.length" class="none state">
      <b>{{ q.trim() ? '찾는 활동이 없어요' : '아직 공개된 활동이 없습니다' }}</b>
      {{ q.trim() ? '검색어를 바꿔보세요.' : '동아리장이 첫 기록을 올리면 여기에 쌓입니다.' }}
    </p>

    <div v-else class="grid">
      <RouterLink
        v-for="p in posts"
        :key="p.id"
        class="card"
        :style="catVars(p.category)"
        :to="`/posts/${p.id}`">
        <div class="shot" :style="p.photo ? { backgroundImage: `url(${p.photo})` } : null">
          <span v-if="!p.photo">{{ postEmoji(p.id) }}</span>
        </div>
        <div class="body">
          <p class="meta">
            <span class="club">{{ p.club_name }}</span>
            <span class="dot" aria-hidden="true">·</span>
            <span>{{ dateText(p.activity_date) }}</span>
          </p>
          <h2>
            {{ p.title }}
            <span v-if="p.is_public === false" class="tag private">비공개</span>
          </h2>
          <p class="excerpt">{{ p.excerpt }}</p>
          <div v-if="p.tags?.length" class="tags">
            <span v-for="t in p.tags" :key="t" class="tag">{{ t }}</span>
          </div>
        </div>
      </RouterLink>
    </div>

    <!-- 바닥 — 관찰자가 여기 닿으면 다음 배치를 부른다 -->
    <div ref="tailEl" class="tail">
      <p v-if="loading" class="more"><span class="pulse"></span> 불러오는 중…</p>
      <p v-else-if="error && posts.length" class="warn">{{ error }}</p>
      <p v-else-if="!hasMore && posts.length" class="end"><i></i>여기까지입니다 · {{ total }}건</p>
    </div>
  </div>
</template>

<style scoped>
:focus-visible {
  outline: 2.5px solid var(--accent);
  outline-offset: 3px;
  border-radius: 8px;
}

.wrap {
  max-width: 1160px;
  margin: 0 auto;
  padding: clamp(36px, 6vh, 70px) clamp(20px, 4vw, 56px) 80px;
}

/* ── 머리 — 왼쪽 위가 검색이다 ── */
.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  margin-bottom: clamp(28px, 4vh, 44px);
}
.head-l {
  min-width: 0;
  flex: 1;
}
.head h1 {
  margin: 0 0 6px;
  font-size: clamp(38px, 4.6vw, 62px);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1;
}
.head .sub {
  margin: 0;
  font-size: 13px;
  color: var(--dim);
}
.head-r {
  text-align: right;
  line-height: 1.75;
  flex: none;
}
.head-r a {
  color: var(--accent);
  font-weight: 700;
}

.search {
  position: relative;
  margin-top: 18px;
  max-width: 380px;
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

/* ── 카드 격자 — 가로 3개 ── */
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: clamp(18px, 2.4vw, 28px);
  align-items: start;
}

/* 생김새는 동아리 타임라인 카드와 맞춘다 */
.card {
  display: block;
  text-decoration: none;
  color: inherit;
  background: var(--card);
  border: var(--border);
  border-radius: var(--r-card);
  overflow: hidden;
  transition: box-shadow var(--t-hover), transform var(--t-hover);
}
.card:hover {
  box-shadow: 0 14px 34px var(--shadowUp);
  transform: translateY(-2px);
}
.card .shot {
  height: 190px;
  background: linear-gradient(150deg, var(--ph-a), var(--ph-b));
  background-size: cover;
  background-position: center;
  display: grid;
  place-items: center;
  font-size: 2.6rem;
}
.card .body {
  padding: 15px 17px 17px;
}
.card .meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 7px;
  font-size: 11.5px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
}
.card .meta .club {
  font-weight: 700;
  color: var(--accent);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card h2 {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.45;
}
.card .excerpt {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--dim);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card .tags {
  display: flex;
  gap: 6px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.tag {
  display: inline-block;
  background: var(--chip);
  border: 1px solid var(--line);
  border-radius: var(--r-chip);
  padding: 2px 10px;
  font-size: 11.5px;
  color: var(--dim);
  font-weight: 600;
}
.tag.private {
  color: var(--warnInk);
  background: var(--warnBg);
  border-color: var(--warnLine);
  vertical-align: middle;
}

/* ── 상태 ── */
.state {
  padding: 60px 0 40px;
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

.tail {
  display: flex;
  justify-content: center;
  padding-top: 34px;
  min-height: 40px;
}
.tail .more,
.tail .end {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  color: var(--dim);
  font-size: 12.5px;
}
.tail .pulse,
.tail .end i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--line);
  font-style: normal;
  flex: none;
}
.tail .pulse {
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1.15);
  }
}

@media (prefers-reduced-motion: reduce) {
  .card,
  .tail .pulse {
    transition: none;
    animation: none;
  }
}

@media (max-width: 980px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .head {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
  }
  .head-r {
    text-align: left;
  }
  .search {
    max-width: none;
  }
}
@media (max-width: 620px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
