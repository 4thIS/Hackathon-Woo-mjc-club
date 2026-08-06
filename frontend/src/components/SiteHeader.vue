<script setup>
/* 모든 페이지 공통 헤더 — 디자인 기획 §4.
   로그인 후 우측이 내 정보/관리/관리자로 바뀐다 (기획서 §8 권한별). */
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AuthDialog from './AuthDialog.vue'
import RecommendDialog from './RecommendDialog.vue'
import logoMark from '../assets/logo-mark.png'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const route = useRoute()
const router = useRouter()

async function signOut() {
  await auth.logout()
  // 로그인이 필요한 화면에 있었다면 나가야 한다 (가드가 다시 잡기 전에)
  if (route.meta.auth) router.replace('/')
}
const authDlg = ref(null)   // 로그인·회원가입은 모달이다 (디자인 기획 §6-2)
const recDlg = ref(null)    // 성향 분석 — 설문도 결과도 저장하지 않는다

onMounted(openFromQuery)

/* /login · /signup 이나 라우터 가드가 ?auth= 를 붙여 보낸다 */
function openFromQuery() {
  const which = route.query.auth
  if (which === 'login' || which === 'signup') authDlg.value?.open(which)
}
watch(() => route.query.auth, openFromQuery)
</script>

<template>
  <header class="site-header">
    <div class="container inner">
      <RouterLink to="/" class="brand" aria-label="MJC Club Archive 홈">
        <img :src="logoMark" alt="MJC Club Archive" width="128" height="61">
      </RouterLink>

      <nav>
        <!-- 홈은 왼쪽 로고가 맡는다. 동아리 개설 진입점은 아카이브 화면(제목 옆)에 둔다 -->
        <RouterLink to="/archive">아카이브</RouterLink>
        <!-- 아카이브가 '동아리를 찾는' 곳이라면 피드는 '지금 무슨 일이 있는지' 보는 곳이다 -->
        <RouterLink to="/feed">전체 피드</RouterLink>

        <!-- 이름만으로는 무슨 기능인지 모른다. 마우스를 올리면 한 줄로 알려준다 -->
        <span v-if="auth.isLoggedIn" class="tip-slot"
              data-tip="여섯 문항으로 나에게 맞는 동아리 3곳을 찾아드려요">
          <button class="btn ghost ai-pick latin" @click="recDlg?.open()">
            <span aria-hidden="true">✦</span> AI Pick!
          </button>
        </span>
      </nav>

      <div class="right">
        <template v-if="auth.isLoggedIn">
          <RouterLink v-if="auth.isAdmin" to="/admin" class="btn ghost">관리자</RouterLink>
          <RouterLink to="/me" class="btn ghost">내 정보</RouterLink>
          <button class="btn ghost signout" @click="signOut">로그아웃</button>
        </template>
        <template v-else>
          <button class="btn ghost" @click="authDlg?.open('login')">로그인</button>
          <button class="btn" @click="authDlg?.open('signup')">회원가입</button>
        </template>
      </div>
    </div>

    <AuthDialog ref="authDlg" />
    <RecommendDialog ref="recDlg" :has-key="auth.hasAiKey" />
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
/* 배경이 투명한 로고다. 파란 수채화라 라이트·다크 양쪽에서 그대로 읽힌다 */
.brand { display: inline-flex; align-items: center; line-height: 0; }
.brand img { height: 30px; width: auto; display: block; }
nav { display: flex; align-items: center; gap: 18px; font-size: 14px; margin-right: auto; }
nav .btn { height: 34px; }
nav a.router-link-exact-active { font-weight: 700; }
.right { display: flex; align-items: center; gap: 8px; }
.right .btn { height: 36px; }

/* AI Pick — 유일한 AI 기능이라 눈에 띄어야 한다. '내 정보'(채운 버튼)와
   경쟁하지 않도록 채우지 않고 강조색 테두리·글씨로만 세운다 */
.btn.ai-pick {
  color: var(--accent);
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  font-weight: 800;
  letter-spacing: -.01em;
  gap: 5px;
}
.btn.ai-pick:hover {
  background: color-mix(in srgb, var(--accent) 16%, transparent);
}
.btn.ai-pick span { font-size: 12px; line-height: 1; }

/* 호버 설명 — 헤더 아래로 흘러나온다 (헤더는 overflow 를 자르지 않는다) */
.tip-slot { position: relative; display: inline-flex; }
.tip-slot::after {
  content: attr(data-tip);
  position: absolute; top: calc(100% + 10px); left: 0;
  transform: translateY(-4px);
  padding: 8px 13px; border-radius: 11px;
  background: var(--card); border: var(--border);
  box-shadow: 0 8px 22px var(--shadow);
  font-size: 12.5px; font-weight: 600; color: var(--dim);
  white-space: nowrap; pointer-events: none;
  opacity: 0; transition: opacity .18s ease, transform .18s ease;
}
.tip-slot:hover::after, .tip-slot:focus-within::after { opacity: 1; transform: none; }

/* 로그아웃 — 되돌리는 동작이라 붉은 계열 (취소·탈퇴와 같은 토큰) */
.right .btn.signout { color: var(--dangerInk); }
.right .btn.signout:hover { border-color: var(--dangerLine); background: var(--dangerBg); }
@media (max-width: 700px) { nav { display: none; } }
</style>
