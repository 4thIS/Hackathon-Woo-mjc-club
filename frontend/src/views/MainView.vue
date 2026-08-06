<script setup>
/* 메인. 디자인 기획 §5.1 (곡선 캐러셀 + 스크롤 2단 스냅 + 브랜드 섹션)
 *
 * 레이아웃
 *   [헤더 64]
 *   [① 캐러셀  100vh − 64 − 타이틀높이]   ← scroll-snap 1
 *   [② 타이틀 148~188px + 브랜드 섹션]     ← scroll-snap 2 (타이틀이 경첩)
 *
 * html 에 거는 스냅 규칙은 scoped CSS 로 안 먹는다. documentElement 에 클래스를
 * 붙였다가 이 화면을 벗어날 때 반드시 뗀다 (다른 페이지에 스냅이 남으면 안 된다).
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import MainCarousel from '../components/MainCarousel.vue'
import MainBrandSection from '../components/MainBrandSection.vue'

const router = useRouter()

const posts = ref([])
const stats = ref(null)
const loading = ref(true)
const notice = ref('')

onMounted(async () => {
  document.documentElement.classList.add('main-snap')

  const [h, s] = await Promise.allSettled([api.posts.highlights(12), api.stats()])

  if (h.status === 'fulfilled') {
    posts.value = h.value ?? []                 // 계약: PostSummary[] (docs/api.md §3)
    if (!posts.value.length) notice.value = '아직 공개된 활동 기록이 없습니다.'
  } else {
    notice.value = '활동 기록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.'
  }

  if (s.status === 'fulfilled') stats.value = s.value

  loading.value = false
})

onBeforeUnmount(() => {
  document.documentElement.classList.remove('main-snap')
})

function openPost(post) {
  router.push(`/posts/${post.id}`)
}
</script>

<template>
  <div class="main">
    <div class="stage-wrap">
      <MainCarousel :posts="posts" :loading="loading" :message="notice" @select="openPost" />
    </div>

    <MainBrandSection :stats="stats" />
  </div>
</template>

<style scoped>
.main { --title-h: clamp(148px, 19vh, 188px); }

/* ① 캐러셀 화면 */
.stage-wrap {
  scroll-snap-align: start;
  position: relative;
  height: calc(100vh - var(--header-h) - var(--title-h));
  min-height: 400px;
}
</style>

<!-- html 에 거는 규칙은 scoped 로 안 된다. .main-snap 이 붙은 동안에만 적용된다 -->
<style>
html.main-snap {
  scroll-snap-type: y mandatory;
  scroll-padding-top: var(--header-h);
  scroll-behavior: smooth;
}
@media (prefers-reduced-motion: reduce) {
  html.main-snap { scroll-behavior: auto; }
}
</style>
