<script setup>
/* 모든 페이지 공통 헤더 — 디자인 기획 §4.
   로그인 후 우측이 내 정보/관리/관리자로 바뀐다 (기획서 §8 권한별). */
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const theme = ref('light')

onMounted(() => {
  const saved = localStorage.getItem('theme')
  theme.value = saved ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  apply()
})

function apply() {
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('theme', theme.value)
}

function toggle() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  apply()
}
</script>

<template>
  <header class="site-header">
    <div class="container inner">
      <RouterLink to="/" class="brand brand-title">MJC Club Archive</RouterLink>

      <nav>
        <RouterLink to="/">홈</RouterLink>
        <RouterLink to="/archive">둘러보기</RouterLink>
        <RouterLink to="/clubs/new">동아리 개설</RouterLink>
      </nav>

      <div class="right">
        <button class="btn ghost icon" @click="toggle" aria-label="테마 전환">◐</button>
        <template v-if="auth.isLoggedIn">
          <RouterLink v-if="auth.isAdmin" to="/admin" class="btn ghost">관리자</RouterLink>
          <RouterLink to="/me" class="btn">내 정보</RouterLink>
        </template>
        <template v-else>
          <RouterLink to="/login" class="btn ghost">로그인</RouterLink>
          <RouterLink to="/signup" class="btn">회원가입</RouterLink>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.site-header {
  position: sticky; top: 0; z-index: 50;
  height: var(--header-h);
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
}
.inner { display: flex; align-items: center; gap: 24px; height: 100%; }
.brand { font-size: 17px; letter-spacing: -.02em; }
nav { display: flex; gap: 18px; font-size: 14px; margin-right: auto; }
nav a.router-link-exact-active { font-weight: 700; }
.right { display: flex; align-items: center; gap: 8px; }
.right .btn { height: 36px; }
@media (max-width: 700px) { nav { display: none; } }
</style>
