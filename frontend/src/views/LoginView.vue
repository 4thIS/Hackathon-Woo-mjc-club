<script setup>
/* T1 — 로그인 (담당 wj). 명세: api.md §2 · 기획서 §4.2
 *
 * 미인증 계정도 로그인은 성공한다. 권한만 비로그인 수준이고, 안내는 내 정보에서 한다.
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const pending = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  pending.value = true
  try {
    await auth.login(email.value.trim(), password.value)
    router.replace(typeof route.query.next === 'string' ? route.query.next : '/')
  } catch (e) {
    error.value = e.message
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="container narrow">
    <h1 class="page-title">로그인</h1>
    <p class="sub top">학교 이메일로 로그인합니다.</p>

    <form class="card form" @submit.prevent="submit">
      <div class="fld">
        <label for="email">학교 이메일</label>
        <input id="email" v-model="email" type="email" autocomplete="username"
               placeholder="26011234@mjc.ac.kr" required>
      </div>

      <div class="fld">
        <label for="pw">비밀번호</label>
        <input id="pw" v-model="password" type="password" autocomplete="current-password" required>
      </div>

      <p v-if="error" class="warn">{{ error }}</p>

      <button class="btn wide" type="submit" :disabled="pending">
        {{ pending ? '확인 중…' : '로그인' }}
      </button>

      <p class="swap">
        아직 계정이 없나요?
        <RouterLink class="link" to="/signup">회원가입</RouterLink>
      </p>
    </form>
  </div>
</template>

<style scoped>
.narrow { width: min(460px, calc(100vw - 40px)); padding: clamp(36px, 7vh, 72px) 0 90px; }
.top { margin: 8px 0 24px; }
.form { padding: 24px; }
.form:hover { transform: none; box-shadow: 0 5px 16px var(--shadow); }
.fld { margin-bottom: 16px; }
.warn { margin: 0 0 14px; }
.wide { width: 100%; }
.swap { margin: 16px 0 0; text-align: center; font-size: 13.5px; color: var(--dim); }
.swap .link { color: var(--accent); font-weight: 700; text-decoration: underline; }
</style>
