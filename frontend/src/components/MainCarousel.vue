<script setup>
/* 메인 곡선 캐러셀 — 디자인 기획 §5.1 / mockups/main.html 이식.
 *
 * 기하 값은 확정이다. 임의로 바꾸지 않는다.
 *   R:1500 big:1.5 small:0.25 tilt:0.42 stepPx:268 stem:36 cardH:164 damping:0.94 clickSlop:6
 *   무대 높이 660px 미만이면 big 1.5 → 1.26 (카드 상단 잘림 방지)
 *
 * 호 위 SVG 라벨은 활동 날짜다 — 이 띠 자체가 타임라인이다.
 * 동아리명은 카드 사진 왼쪽 위에 북마크로 얹는다.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { catKey, catEmoji } from './ClubCategory'

const props = defineProps({
  posts: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  message: { type: String, default: '' },
})
const emit = defineEmits(['select'])

/* ── 확정 기하 ─────────────────────────────────────────── */
const GEO = {
  R: 1500, big: 1.5, small: 0.25, tilt: 0.42, stepPx: 268,
  stem: 36, cardH: 164, damping: 0.94, clickSlop: 6,
}
const STEP = GEO.stepPx / GEO.R
const GAP = STEP * 2

const wrapAngle = (raw, total) => {
  const a = ((raw % total) + total) % total
  return a > total / 2 ? a - total : a
}

function visibleHalf(R, cy, width, topPad = -60) {
  const halfX = Math.asin(Math.min(0.999, (width / 2 + 120) / R))
  const cosLim = (topPad - cy) / R
  const halfY = cosLim >= 1 ? 0 : cosLim <= -1 ? Math.PI : Math.acos(cosLim)
  return Math.max(0.15, Math.min(halfX, halfY))
}

function cardTransform(a, half, up, { cx, cy }, big) {
  const { R, small, tilt, stem, cardH } = GEO
  const k = Math.min(1, Math.abs(a) / half)
  const f = (1 - k) ** 1.35
  const scale = small + (big - small) * f
  const dist = up
    ? R - stem * scale - (cardH * scale) / 2
    : R + stem * scale + (cardH * scale) / 2
  return {
    x: cx + dist * Math.sin(a),
    y: cy + dist * Math.cos(a),
    scale,
    opacity: 0.25 + 0.75 * f,
    rotate: (-a * 180 / Math.PI) * tilt,
  }
}

/* ── 상태 ─────────────────────────────────────────────── */
const stage = ref(null)
const stageW = ref(1200)
const stageH = ref(700)
const offset = ref(0)

const reduced = typeof matchMedia === 'function'
  ? matchMedia('(prefers-reduced-motion: reduce)').matches
  : false

const frame = computed(() => {
  const w = stageW.value
  const h = stageH.value
  const R = GEO.R
  // 무대가 낮으면 가운데 카드가 위로 잘린다. 배율을 줄여 눌러 담는다
  const big = h < 660 ? 1.26 : 1.5
  const cx = w / 2
  const cy = h * 0.53 - R
  const half = visibleHalf(R, cy, w)

  const pt = (a) => ({ x: cx + R * Math.sin(a), y: cy + R * Math.cos(a) })
  const arc = (a0, a1) => {
    const p = pt(a0)
    const q = pt(a1)
    return `M${p.x},${p.y} A${R},${R} 0 0 0 ${q.x},${q.y}`
  }

  const list = props.posts
  const total = Math.max(list.length * STEP + GAP, GAP)

  const items = []
  list.forEach((p, i) => {
    const a = wrapAngle(i * STEP - offset.value, total)
    if (Math.abs(a) > half) return
    const up = i % 2 === 1
    const t = cardTransform(a, half, up, { cx, cy }, big)
    const ax = cx + R * Math.sin(a)
    const ay = cy + R * Math.cos(a)
    const edge = up ? R - GEO.stem * t.scale : R + GEO.stem * t.scale
    const ld = up ? R + 24 * t.scale + 8 : R - 24 * t.scale - 8
    const lx = cx + ld * Math.sin(a)
    const ly = cy + ld * Math.cos(a)
    items.push({
      post: p, a, up, t,
      dot: { cx: ax, cy: ay, r: 3.5 * t.scale + 1.5 },
      stem: { x1: ax, y1: ay, x2: cx + edge * Math.sin(a), y2: cy + edge * Math.cos(a), w: 2.2 * t.scale + 0.7 },
      label: { x: lx, y: ly + (up ? 13 : 0), size: Math.max(9, 10 * t.scale + 3), rotate: `rotate(${t.rotate} ${lx} ${ly})` },
    })
  })
  // 작은 카드부터 그려야 가운데 카드가 맨 위로 온다
  items.sort((m, n) => m.t.scale - n.t.scale)

  // 트랙 끝 마감 — 처음과 끝의 경계
  const ticks = []
  if (list.length) {
    ;[-GAP / 2, list.length * STEP - STEP + GAP / 2].forEach((edgeAngle) => {
      const a = wrapAngle(edgeAngle - offset.value, total)
      if (Math.abs(a) > half) return
      ticks.push({
        x1: cx + (R - 14) * Math.sin(a), y1: cy + (R - 14) * Math.cos(a),
        x2: cx + (R + 14) * Math.sin(a), y2: cy + (R + 14) * Math.cos(a),
      })
    })
  }

  /* 마지막 카드와 첫 카드 사이는 트랙이 아니다. 그 구간의 호를 지워 고리를 끊는다 —
     끝이 어디인지 선 자체로 보인다. 갭 = 두 마감 표시 사이 한 칸(STEP) */
  const bands = []
  if (!list.length) {
    bands.push(arc(-half, half))
  } else {
    const gc = wrapAngle((list.length - 0.5) * STEP + GAP / 2 - offset.value, total)
    const g0 = gc - STEP / 2
    const g1 = gc + STEP / 2
    if (g1 <= -half || g0 >= half) {
      bands.push(arc(-half, half))
    } else {
      if (g0 > -half) bands.push(arc(-half, g0))
      if (g1 < half) bands.push(arc(g1, half))
    }
  }

  return { w, h, bands, items, ticks }
})

/* ── 카드 표현 ─────────────────────────────────────────── */
/* PostSummary.category = 동아리 분야 (docs/api.md §0.4). 값이 없을 때만 기본 그라데이션 */
const catOf = (p) => catKey(p?.category)

function photoStyle(p) {
  const cat = catOf(p)
  const grad = `linear-gradient(145deg, var(--cat-${cat}-a), var(--cat-${cat}-b))`
  return p.photo
    ? { backgroundImage: `url("${p.photo}")` }
    : { backgroundImage: grad }
}
const emojiOf = (p) => (p.photo ? null : catEmoji(p?.category))

/* 호 위 라벨 = 활동 날짜 (타임라인 표기는 타임라인과 같은 점 구분자) */
const dateText = (d) => (d ? String(d).replaceAll('-', '.') : '')

function cardStyle(it) {
  return {
    left: `${it.t.x}px`,
    top: `${it.t.y}px`,
    transform: `translate(-50%,-50%) rotate(${it.t.rotate}deg) scale(${it.t.scale})`,
    opacity: it.t.opacity,
    zIndex: Math.round(it.t.scale * 1000),
  }
}

/* ── 드래그 + 관성 ─────────────────────────────────────── */
const dragging = ref(false)
let lastX = 0, lastT = 0, downX = 0, downY = 0, moved = 0
let vel = 0, raf = null, gen = 0, pressed = null

function stopRaf() {
  gen += 1
  if (raf) { cancelAnimationFrame(raf); raf = null }
}

function glide() {
  if (reduced) return                 // 관성 생략
  const my = ++gen
  const step = () => {
    if (my !== gen) return             // 뒤이어 시작된 관성이 있으면 이 루프는 접는다
    vel *= GEO.damping
    offset.value += vel
    if (Math.abs(vel) > 0.00008) raf = requestAnimationFrame(step)
    else raf = null
  }
  step()
}

function onPointerDown(e) {
  dragging.value = true
  moved = 0
  // 포인터 캡처 후 click 은 stage 로 간다 — 눌린 카드를 기억해 release 에서 판정
  const card = e.target?.closest?.('.card')
  pressed = card?.dataset?.id ?? null
  stage.value?.setPointerCapture?.(e.pointerId)
  lastX = downX = e.clientX
  downY = e.clientY
  lastT = performance.now()
  vel = 0
  stopRaf()
}

function onPointerMove(e) {
  if (!dragging.value) return
  const now = performance.now()
  const dx = e.clientX - lastX
  const dt = Math.max(1, now - lastT)
  moved = Math.max(moved, Math.hypot(e.clientX - downX, e.clientY - downY))
  offset.value -= dx / GEO.R          // 끄는 방향의 반대로 흐른다
  vel = (-(dx / GEO.R) / dt) * 16
  lastX = e.clientX
  lastT = now
}

function release() {
  if (!dragging.value) return
  dragging.value = false
  if (moved < GEO.clickSlop) {        // 6px 미만이면 끈 게 아니라 누른 것
    if (pressed !== null) open(pressed)
    pressed = null
    return
  }
  pressed = null
  glide()
}

function open(id) {
  const p = props.posts.find((x) => String(x.id) === String(id))
  if (p) emit('select', p)
}

/* ── 키보드 ───────────────────────────────────────────── */
function nudge(dir) {
  stopRaf()
  const target = offset.value + dir * STEP
  if (reduced) { offset.value = target; return }
  const from = offset.value
  const t0 = performance.now()
  const dur = 260
  const my = ++gen
  const step = () => {
    if (my !== gen) return
    const k = Math.min(1, (performance.now() - t0) / dur)
    const e = 1 - (1 - k) ** 3
    offset.value = from + (target - from) * e
    if (k < 1) raf = requestAnimationFrame(step)
    else raf = null
  }
  step()
}

function onKeydown(e) {
  if (e.key === 'ArrowRight') { e.preventDefault(); nudge(1) }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); nudge(-1) }
}

/* ── 자동 회전 ────────────────────────────────────────── */
/* offset 이 커지면 카드는 왼쪽으로 흐른다 — 원의 중심이 화면 위에 있으므로 시계방향이다.
 * 카드 한 칸에 9초. 손이 올라가 있거나 관성이 도는 동안은 멈춘다. */
const AUTO_PER_SEC = STEP / 9
let autoRaf = null
let autoLast = 0

function autoSpin(t) {
  autoRaf = requestAnimationFrame(autoSpin)
  const dt = autoLast ? Math.min(120, t - autoLast) : 16   // 탭 전환 후 튀지 않게 상한
  autoLast = t
  if (dragging.value || raf) return
  offset.value += (AUTO_PER_SEC * dt) / 1000
}

/* ── 크기 추적 ────────────────────────────────────────── */
let ro = null
function measure() {
  const el = stage.value
  if (!el) return
  stageW.value = el.clientWidth || stageW.value
  stageH.value = el.clientHeight || stageH.value
}

onMounted(() => {
  measure()
  if (typeof ResizeObserver === 'function') {
    ro = new ResizeObserver(measure)
    ro.observe(stage.value)
  }
  addEventListener('resize', measure)
  if (!reduced) autoRaf = requestAnimationFrame(autoSpin)
})

onBeforeUnmount(() => {
  stopRaf()
  if (autoRaf) cancelAnimationFrame(autoRaf)
  ro?.disconnect()
  removeEventListener('resize', measure)
})
</script>

<template>
  <section
    ref="stage"
    class="stage"
    :class="{ dragging }"
    tabindex="0"
    role="region"
    aria-label="공개 활동 기록 캐러셀 — 좌우 방향키로 넘길 수 있습니다"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="release"
    @pointercancel="release"
    @keydown="onKeydown"
  >
    <svg class="band" :viewBox="`0 0 ${frame.w} ${frame.h}`" aria-hidden="true">
      <path
        v-for="(d, i) in frame.bands" :key="`band-${i}`"
        :d="d" fill="none" stroke="var(--band)" stroke-width="3.5" stroke-linecap="round"
      />

      <template v-for="it in frame.items" :key="`g-${it.post.id}`">
        <circle :cx="it.dot.cx" :cy="it.dot.cy" :r="it.dot.r" fill="var(--band)" :opacity="it.t.opacity" />
        <line
          :x1="it.stem.x1" :y1="it.stem.y1" :x2="it.stem.x2" :y2="it.stem.y2"
          stroke="var(--band)" :stroke-width="it.stem.w" :opacity="it.t.opacity"
        />
        <!-- 호 위의 라벨 = 활동 날짜. 띠를 따라 시간이 흐른다 -->
        <text
          :x="it.label.x" :y="it.label.y" text-anchor="middle"
          :font-size="it.label.size" font-weight="700" fill="var(--dim)"
          :opacity="it.t.opacity" font-family="inherit" :transform="it.label.rotate"
          style="font-variant-numeric: tabular-nums"
        >{{ dateText(it.post.activity_date) }}</text>
      </template>

      <line
        v-for="(tk, i) in frame.ticks" :key="`tick-${i}`"
        :x1="tk.x1" :y1="tk.y1" :x2="tk.x2" :y2="tk.y2"
        stroke="var(--band)" stroke-width="3.5" stroke-linecap="round"
      />
    </svg>

    <div class="cards">
      <button
        v-for="it in frame.items"
        :key="it.post.id"
        class="card"
        type="button"
        :data-id="it.post.id"
        :style="cardStyle(it)"
        :aria-label="`${it.post.club_name} — ${it.post.title}`"
        @keydown.enter.prevent="open(it.post.id)"
        @keydown.space.prevent="open(it.post.id)"
      >
        <span class="photo" :style="photoStyle(it.post)" :data-emoji="emojiOf(it.post)"></span>
        <span class="ribbon">{{ it.post.club_name }}</span>
        <span class="ttl">{{ it.post.title }}</span>
      </button>
    </div>

    <p v-if="message" class="empty">{{ message }}</p>

    <div class="drag-hint"><i>↔</i> 드래그해서 넘기기</div>
  </section>
</template>

<style scoped>
.stage {
  position: relative;
  height: 100%;
  overflow: hidden;
  cursor: grab;
  user-select: none;
  touch-action: pan-y;
  z-index: 0;
}
.stage.dragging { cursor: grabbing; }

.band, .cards { position: absolute; inset: 0; }
.cards { pointer-events: none; }

.empty {
  position: absolute; left: 50%; top: 46%; transform: translate(-50%, -50%);
  margin: 0; text-align: center; font-size: 14px; color: var(--dim);
  max-width: 34ch; pointer-events: none;
}

.drag-hint {
  position: absolute; right: clamp(18px, 3.5vw, 42px); bottom: 16px;
  font-size: 12px; color: var(--dim);
  display: flex; align-items: center; gap: 7px;
  z-index: 900; pointer-events: none;
}
.drag-hint i { font-style: normal; animation: sway 2.6s ease-in-out infinite; }
@keyframes sway {
  0%, 100% { transform: translateX(-3px); }
  50% { transform: translateX(3px); }
}

/* 활동 카드 — 사진 + 제목 2줄만 */
.card {
  position: absolute; width: 210px;
  pointer-events: auto; cursor: pointer;
  display: block; padding: 0; text-align: left;
  background: var(--card);
  border: var(--border);
  border-radius: 18px;
  overflow: hidden;
  color: inherit; font: inherit;
  box-shadow: 0 5px 16px var(--shadow);
  transition: box-shadow var(--t-hover);
}
.card:hover { box-shadow: 0 12px 34px var(--shadowUp); }

.photo {
  display: grid; place-items: center;
  height: 120px;
  background-size: cover; background-position: center;
}
.photo::after { content: attr(data-emoji); font-size: 2.4rem; opacity: .55; }

/* 동아리명 — 사진 왼쪽 위에 걸린 북마크. 아래끝이 V 로 파여 띠처럼 보인다 */
.ribbon {
  position: absolute; top: 0; left: 13px; z-index: 2;
  max-width: calc(100% - 30px);
  padding: 6px 9px 12px;
  background: var(--accent); color: var(--onAccent);
  font-size: 11px; font-weight: 700; line-height: 1.2; letter-spacing: -.01em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  clip-path: polygon(0 0, 100% 0, 100% 100%, 50% calc(100% - 6px), 0 100%);
}

.ttl {
  display: -webkit-box;
  padding: 11px 13px 13px;
  font-size: 14px; font-weight: 700; line-height: 1.35; letter-spacing: -.01em;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

@media (prefers-reduced-motion: reduce) {
  .drag-hint i { animation: none; }
}
</style>
