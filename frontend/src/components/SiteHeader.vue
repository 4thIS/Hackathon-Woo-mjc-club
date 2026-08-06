<script setup>
/* 모든 페이지 공통 헤더 — 디자인 기획 §4.
   로그인 후 우측이 내 정보/관리/관리자로 바뀐다 (기획서 §8 권한별). */
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AuthDialog from './AuthDialog.vue'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const route = useRoute()
const router = useRouter()

async function signOut() {
  await auth.logout()
  // 로그인이 필요한 화면에 있었다면 나가야 한다 (가드가 다시 잡기 전에)
  if (route.meta.auth) router.replace('/')
}
const theme = ref('light')
const authDlg = ref(null)   // 로그인·회원가입은 모달이다 (디자인 기획 §6-2)

onMounted(() => {
  const saved = localStorage.getItem('theme')
  theme.value = saved ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  apply()
  openFromQuery()
})

/* /login · /signup 이나 라우터 가드가 ?auth= 를 붙여 보낸다 */
function openFromQuery() {
  const which = route.query.auth
  if (which === 'login' || which === 'signup') authDlg.value?.open(which)
}
watch(() => route.query.auth, openFromQuery)

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
          <button class="btn ghost" @click="signOut">로그아웃</button>
        </template>
        <template v-else>
          <button class="btn ghost" @click="authDlg?.open('login')">로그인</button>
          <button class="btn" @click="authDlg?.open('signup')">회원가입</button>
        </template>
      </div>
    </div>

    <AuthDialog ref="authDlg" />
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
