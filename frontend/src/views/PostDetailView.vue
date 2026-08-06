<script setup>
/* 활동 글 상세
 * api.md §3 `GET /posts/{id}` · §6 `POST /posts/{id}/like` · §0.1 에러
 * 기획서 §6 — 본문은 평문(줄바꿈만), 좋아요는 로그인 사용자만 1인 1회, 댓글 없음.
 * 목업이 없는 화면이라 디자인 §6 제작 규칙을 따른다 — 토큰만, 등장 애니메이션 없음,
 * 카드·사진 폴백·태그칩·날짜 표기는 ClubTimeline 과 톤을 맞춘다.
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api, { ApiError } from '../api'
import { useAuth } from '../stores/auth'
import { catVars, postEmoji } from '../components/ClubCategory'

const props = defineProps({ id: { type: String, required: true } })

const route = useRoute()
const auth = useAuth()

const post = ref(null)
const loading = ref(true)
const notFound = ref(false)     // 비공개 글 무권한 포함 (api.md §9-5 — 존재를 숨긴다)
const loadError = ref('')

const category = ref('')        // 글 응답엔 분야가 없다 — 폴백 그라데이션용으로만 따로 조회
const liking = ref(false)
const likeError = ref('')

const phVars = computed(() => catVars(category.value))
const photos = computed(() => post.value?.photos ?? [])
const emoji = computed(() => postEmoji(post.value?.id ?? props.id))

const dateText = (d) => (d ? String(d).replaceAll('-', '.') : '')

/* ── 사진 슬라이드 ──
 * 스크롤 스냅으로 넘긴다 — 손가락 스와이프·트랙패드가 공짜로 따라온다.
 * 사진 비율이 제각각이라 칸 높이를 고정하고 contain 으로 가운데에 앉힌다. */
const track = ref(null)
const shotIdx = ref(0)
const slideMotion =
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
    ? 'auto'
    : 'smooth'

function goShot(i) {
  const el = track.value
  if (!el) return
  const n = photos.value.length
  const to = Math.min(Math.max(i, 0), n - 1)
  el.scrollTo({ left: el.clientWidth * to, behavior: slideMotion })
  shotIdx.value = to
}

/* 스크롤이 멈춘 자리로 현재 장을 되읽는다 (스와이프·키보드 모두 여기로 모인다) */
function onTrackScroll() {
  const el = track.value
  if (!el || !el.clientWidth) return
  shotIdx.value = Math.round(el.scrollLeft / el.clientWidth)
}

const authorLine = computed(() => {
  const a = post.value?.author
  if (!a) return ''
  return [a.name, a.dept].filter(Boolean).join(' · ')
})

/* 좋아요는 `인증`(로그인 + 이메일 인증). 누를 수 없는 이유를 그대로 안내한다. */
const likeBlocked = computed(() => !auth.isLoggedIn || !auth.isVerified)
const likeNotice = computed(() => {
  if (auth.isLoggedIn && !auth.isVerified) return '이메일 인증을 마치면 좋아요를 누를 수 있습니다.'
  if (!auth.isLoggedIn) return '로그인하면 좋아요를 누를 수 있습니다.'
  return ''
})

async function loadCategory(clubId) {
  // 폴백 이모지 배경의 분야색을 얻기 위한 보조 조회 — 실패해도 화면은 그대로 산다
  if (!clubId) return
  try {
    const c = await api.clubs.detail(clubId)
    category.value = c?.category ?? ''
  } catch { /* 기본 그라데이션(academic)으로 남는다 */ }
}

async function load() {
  loading.value = true
  notFound.value = false
  loadError.value = ''
  likeError.value = ''
  post.value = null
  category.value = ''
  try {
    const p = await api.posts.detail(props.id)
    post.value = p
    if (!(p?.photos?.length)) loadCategory(p?.club_id)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound.value = true
    else loadError.value = e?.message ?? '글을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

async function toggleLike() {
  if (!post.value || likeBlocked.value || liking.value) return
  liking.value = true
  likeError.value = ''
  try {
    const r = await api.posts.like(post.value.id)
    post.value.liked_by_me = !!r?.liked
    post.value.like_count = r?.like_count ?? post.value.like_count
  } catch (e) {
    likeError.value = e?.message ?? '좋아요를 처리하지 못했습니다.'
  } finally {
    liking.value = false
  }
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <!-- 로딩 — 실제 레이아웃과 같은 골격을 두어 내용이 들어와도 흔들리지 않는다 -->
  <article v-if="loading" class="post" aria-busy="true">
    <div class="head">
      <p class="sub ph-line s"></p>
      <div class="ph-line l"></div>
      <p class="sub ph-line m"></p>
    </div>
    <div class="shot ph-box"></div>
    <div class="body">
      <div class="ph-line b"></div>
      <div class="ph-line b"></div>
      <div class="ph-line b short"></div>
    </div>
    <span class="sr">불러오는 중</span>
  </article>

  <!-- 없음 — 비공개 글 무권한도 여기로 온다. 권한 얘기를 쓰지 않는다(존재를 숨긴다) -->
  <div v-else-if="notFound" class="state">
    <div class="state-ico" aria-hidden="true">🔎</div>
    <h1 class="page-title">글을 찾을 수 없습니다</h1>
    <p class="sub">주소가 바뀌었거나 삭제된 글일 수 있습니다.</p>
    <RouterLink class="btn" to="/archive">동아리 둘러보기</RouterLink>
  </div>

  <div v-else-if="loadError" class="state">
    <div class="state-ico" aria-hidden="true">⚠️</div>
    <h1 class="page-title">글을 불러오지 못했습니다</h1>
    <p class="sub">{{ loadError }}</p>
    <button class="btn" @click="load">다시 시도</button>
  </div>

  <article v-else-if="post" class="post" :style="phVars">
    <div class="head">
      <RouterLink class="club" :to="`/clubs/${post.club_id}`">{{ post.club_name }}</RouterLink>

      <h1 class="page-title">
        {{ post.title }}
        <span v-if="post.is_public === false" class="warn badge">비공개</span>
      </h1>

      <p class="meta">
        <span v-if="post.activity_date">{{ dateText(post.activity_date) }}</span>
        <span v-if="authorLine" class="dot" aria-hidden="true">·</span>
        <span v-if="authorLine">{{ authorLine }}</span>
      </p>
    </div>

    <!-- 사진: 좌우로 넘겨 본다. 비율이 달라도 칸 가운데에 온전히 들어온다 -->
    <div v-if="photos.length" class="gallery"
         role="group" :aria-label="`사진 ${photos.length}장`"
         @keydown.left.prevent="goShot(shotIdx - 1)"
         @keydown.right.prevent="goShot(shotIdx + 1)">
      <div ref="track" class="track" tabindex="0" @scroll.passive="onTrackScroll">
        <div v-for="(src, i) in photos" :key="src" class="slide">
          <img :src="src" :loading="i ? 'lazy' : 'eager'" :alt="`${post.title} 사진 ${i + 1}`">
        </div>
      </div>

      <template v-if="photos.length > 1">
        <button class="nav prev" type="button" aria-label="이전 사진"
                :disabled="shotIdx === 0" @click="goShot(shotIdx - 1)">‹</button>
        <button class="nav next" type="button" aria-label="다음 사진"
                :disabled="shotIdx === photos.length - 1" @click="goShot(shotIdx + 1)">›</button>

        <div class="dots">
          <button v-for="(src, i) in photos" :key="src" type="button"
                  class="dot" :class="{ on: i === shotIdx }"
                  :aria-label="`${i + 1}번째 사진`" :aria-current="i === shotIdx"
                  @click="goShot(i)"></button>
        </div>
        <p class="count sub">{{ shotIdx + 1 }} / {{ photos.length }}</p>
      </template>
    </div>
    <div v-else class="shot fallback" aria-hidden="true">{{ emoji }}</div>

    <!-- 본문은 평문이다 (api.md §9-3). 줄바꿈만 살린다 -->
    <div class="body">{{ post.body }}</div>

    <div v-if="post.tags?.length" class="tags">
      <span v-for="t in post.tags" :key="t" class="tag">{{ t }}</span>
    </div>

    <div class="acts">
      <button class="like" type="button"
              :class="{ on: post.liked_by_me }"
              :disabled="likeBlocked || liking"
              :aria-pressed="!!post.liked_by_me"
              :title="likeNotice || (post.liked_by_me ? '좋아요 취소' : '좋아요')"
              @click="toggleLike">
        <span aria-hidden="true">{{ post.liked_by_me ? '♥' : '♡' }}</span>
        좋아요 <b>{{ post.like_count ?? 0 }}</b>
      </button>

      <RouterLink v-if="post.can_edit" class="btn ghost" :to="`/posts/${post.id}/edit`">수정</RouterLink>
    </div>

    <p v-if="likeError" class="warn note">{{ likeError }}</p>
    <p v-else-if="likeBlocked" class="note sub">
      {{ likeNotice }}
      <RouterLink v-if="!auth.isLoggedIn" class="lk"
                  :to="{ path: route.path, query: { ...route.query, auth: 'login' } }">
        로그인하기
      </RouterLink>
      <RouterLink v-else class="lk" to="/me">내 정보로 가기</RouterLink>
    </p>

    <div class="foot">
      <RouterLink class="btn ghost" :to="`/clubs/${post.club_id}`">
        {{ post.club_name }} 활동 기록 전체 보기
      </RouterLink>
    </div>
  </article>
</template>

<style scoped>
.post {
  width: min(820px, calc(100vw - 40px));
  margin: 0 auto;
  padding: clamp(30px, 5vh, 58px) 0 clamp(60px, 9vh, 110px);
}

/* --- 머리 --- */
.head { margin-bottom: clamp(22px, 3.5vh, 34px); }
.club {
  display: inline-block; font-size: 13px; font-weight: 700; color: var(--accent);
  margin-bottom: 10px; border-radius: var(--r-chip);
  transition: opacity var(--t-hover);
}
.club:hover { opacity: .72; }

.head .page-title { margin: 0; }
.badge {
  display: inline-block; padding: 3px 11px; border-radius: var(--r-chip);
  font-size: 13px; font-weight: 700; vertical-align: middle;
  margin-left: 10px; white-space: nowrap;
}

.meta {
  margin: 12px 0 0; font-size: 13px; color: var(--dim); font-weight: 600;
  display: flex; flex-wrap: wrap; gap: 7px; align-items: baseline;
}

/* --- 사진 슬라이드 --- */
.gallery { position: relative; }

.track {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  border-radius: var(--r-card);          /* 판·테두리 없이 사진만 놓는다 */
  scrollbar-width: none;                 /* 넘김 UI 가 따로 있다 */
}
.track::-webkit-scrollbar { display: none; }
.track:focus-visible { outline: 2.5px solid var(--accent); outline-offset: 3px; }

/* 칸 높이를 고정해야 장마다 화면이 튀지 않는다. 사진은 그 안에서 가운데 정렬 */
.slide {
  flex: 0 0 100%; scroll-snap-align: center;
  height: clamp(300px, 52vh, 560px); padding: 10px;
}
/* 칸을 꽉 채운 뒤 contain 으로 맞춘다 — max-height 는 세로 사진에서 칸을 넘긴다 */
.slide img {
  width: 100%; height: 100%; object-fit: contain;
  border-radius: 12px; display: block;
}

.nav {
  position: absolute; top: 50%; transform: translateY(-50%);
  width: 40px; height: 40px; border-radius: 50%;
  border: var(--border); background: var(--card); color: var(--ink);
  font-size: 22px; line-height: 1; cursor: pointer;
  box-shadow: 0 5px 16px var(--shadow);
  transition: border-color var(--t-hover), color var(--t-hover), opacity var(--t-hover);
}
.nav:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.nav:disabled { opacity: .3; cursor: default; }
.nav.prev { left: 12px; }
.nav.next { right: 12px; }

.dots { display: flex; justify-content: center; gap: 7px; margin-top: 12px; }
.dot {
  width: 7px; height: 7px; padding: 0; border-radius: 50%;
  border: none; background: var(--line); cursor: pointer;
  transition: background var(--t-hover), width var(--t-hover);
}
.dot.on { width: 20px; border-radius: 999px; background: var(--accent); }

.count { text-align: center; margin: 7px 0 0; font-variant-numeric: tabular-nums; }

.shot {
  width: 100%; border-radius: var(--r-card); border: var(--border);
  background: var(--chip); display: block;
}
.shot.fallback {
  aspect-ratio: 16 / 9;
  background: linear-gradient(150deg, var(--ph-a), var(--ph-b));
  display: grid; place-items: center; font-size: 3.4rem;
}

/* --- 본문 --- */
.body {
  white-space: pre-wrap;          /* 평문 — 줄바꿈만 살린다 */
  overflow-wrap: anywhere;
  margin: clamp(24px, 4vh, 40px) 0 0;
  font-size: 15.5px; line-height: 1.95;
}

.tags { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 24px; }
.tag {
  display: inline-block; background: var(--chip); border: 1px solid var(--line);
  border-radius: var(--r-chip); padding: 3px 12px;
  font-size: 12px; color: var(--dim); font-weight: 600;
}

/* --- 좋아요·수정 --- */
.acts {
  display: flex; align-items: center; gap: 9px; flex-wrap: wrap;
  margin-top: clamp(26px, 4vh, 40px); padding-top: 22px;
  border-top: 1px solid var(--line);
}
.like {
  display: inline-flex; align-items: center; gap: 8px;
  height: 40px; padding: 0 18px;
  border: var(--border); border-radius: var(--r-btn);
  background: var(--card); color: var(--ink);
  font: inherit; font-weight: 700; cursor: pointer;
  transition: background var(--t-hover), border-color var(--t-hover), color var(--t-hover);
}
.like:hover:not(:disabled) { background: var(--chip); border-color: var(--accent); }
.like.on { color: var(--accent); border-color: var(--accent); }
.like:disabled { opacity: .5; cursor: not-allowed; }
.like b { font-variant-numeric: tabular-nums; }

.note { margin: 14px 0 0; }
.note.sub { font-size: 12.5px; }
.lk { color: var(--accent); font-weight: 700; margin-left: 4px; }
.lk:hover { text-decoration: underline; }

.foot { margin-top: clamp(30px, 5vh, 52px); }

/* --- 빈 상태 (디자인 §6-6) --- */
.state { text-align: center; padding: 90px 20px 120px; color: var(--dim); }
.state-ico { font-size: 2.6rem; line-height: 1; margin-bottom: 14px; }
.state .page-title { color: var(--ink); margin: 0 0 8px; }
.state .btn { margin-top: 18px; }

/* --- 로딩 골격 — 실제와 같은 자리를 미리 잡아 둔다 --- */
.ph-line, .ph-box { background: var(--chip); border-radius: 8px; }
.ph-line { height: 14px; margin: 0 0 10px; }
.ph-line.s { width: 120px; }
.ph-line.l { height: clamp(34px, 5vw, 56px); width: min(100%, 560px); border-radius: 12px; }
.ph-line.m { width: 200px; margin-top: 12px; }
.ph-box { aspect-ratio: 16 / 9; border-radius: var(--r-card); border: var(--border); }
.body .ph-line.b { height: 14px; width: 100%; margin-bottom: 12px; }
.body .ph-line.b.short { width: 62%; }

.sr {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

@media (max-width: 620px) {
  .badge { display: inline-block; margin-left: 0; margin-top: 10px; font-size: 12px; }
  .acts { gap: 8px; }
}
</style>
