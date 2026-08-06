<script setup>
/* T2 · 담당 cw — 메인. 디자인 기획 §5.1 (곡선 캐러셀 + 스크롤 2단 스냅 + 브랜드 섹션)
 *
 * T0 시점에는 스택이 살아 있는지 눈으로 확인하는 최소 화면만 둔다.
 * 캐러셀 기하(R:1500 big:1.5 …)와 스냅 레이아웃은 T2에서 목업 그대로 이식한다.
 */
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../api'

const stats = ref(null)
const clubs = ref([])
const error = ref('')

onMounted(async () => {
  try {
    const [s, c] = await Promise.all([api.stats(), api.clubs.list()])
    stats.value = s
    clubs.value = c.items
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <section class="container hero">
    <p class="eyebrow">mjc hackathon project with Woo</p>
    <h1 class="page-title brand-title">MJC Club Archive</h1>
    <p class="lead">소개글 대신 <strong>지난주에 실제로 뭘 했는지</strong>를 보고 동아리를 고르세요.</p>

    <div v-if="error" class="warn">{{ error }}</div>

    <div v-if="stats" class="stats">
      <div><b>{{ stats.clubs }}</b><span>등록 동아리</span></div>
      <div><b>{{ stats.recruiting }}</b><span>모집중</span></div>
      <div><b>{{ stats.posts }}</b><span>활동 기록</span></div>
      <div><b>{{ stats.categories }}</b><span>분야</span></div>
    </div>

    <!-- TODO(T2): 여기가 곡선 캐러셀 자리 (디자인 기획 §5.1) -->
    <ul class="grid">
      <li v-for="c in clubs" :key="c.id" class="card">
        <RouterLink :to="`/clubs/${c.id}`">
          <p class="card-title">{{ c.name }}</p>
          <p class="sub">{{ c.category }} · {{ c.recruit_status }} · {{ c.member_count }}명</p>
        </RouterLink>
      </li>
    </ul>

    <RouterLink to="/archive" class="btn ghost">아카이브 바로가기 →</RouterLink>
  </section>
</template>

<style scoped>
.hero { padding: 72px 0 120px; }
.lead { font-size: 17px; color: var(--dim); max-width: 46ch; }
.stats { display: flex; gap: 36px; margin: 32px 0 40px; }
.stats div { display: flex; flex-direction: column; }
.stats b { font-size: 28px; font-weight: 800; letter-spacing: -.03em; }
.stats span { font-size: 12.5px; color: var(--dim); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(248px, 1fr)); gap: 16px; padding: 0; margin: 0 0 32px; list-style: none; }
.grid .card { padding: 18px; }
.card-title { margin: 0 0 4px; }
.sub { margin: 0; }
</style>
