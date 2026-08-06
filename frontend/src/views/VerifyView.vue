<script setup>
/* T1 — 이메일 인증 결과 (담당 wj). 명세: api.md §2
 *
 * 백엔드가 /api/auth/verify 처리 후 여기로 302 시킨다 → ?status=ok|expired|invalid
 * 성공하면 세션의 email_verified 가 바뀌었으므로 /me 를 다시 읽는다.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import { useAuth } from '../stores/auth'

const route = useRoute()
const auth = useAuth()

const status = computed(() => route.query.status ?? 'invalid')
const email = ref('')
const resent = ref(false)
const error = ref('')

const VIEW = {
  ok: {
    title: '인증이 완료됐어요',
    body: '이제 동아리 가입 신청과 글 작성을 할 수 있습니다.',
  },
  expired: {
    title: '인증 링크가 만료됐어요',
    body: '링크는 발급 후 24시간 동안만 쓸 수 있습니다. 아래에서 다시 받아주세요.',
  },
  invalid: {
    title: '유효하지 않은 링크예요',
    body: '주소가 잘리지 않았는지 확인해주세요. 계속 안 되면 인증 메일을 다시 받아주세요.',
  },
}
const view = computed(() => VIEW[status.value] ?? VIEW.invalid)

onMounted(() => {
  // 인증 직후엔 서버 상태가 바뀌었다. 화면의 로그인 정보도 맞춰준다.
  if (status.value === 'ok' && auth.isLoggedIn) auth.load()
})

async function resend() {
  error.value = ''
  try {
    await api.auth.resendVerification(email.value.trim())
    resent.value = true
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="container narrow">
    <p class="eyebrow">이메일 인증</p>
    <h1 class="page-title">{{ view.title }}</h1>
    <p class="sub top">{{ view.body }}</p>

    <div class="card box">
      <template v-if="status === 'ok'">
        <div class="row">
          <RouterLink class="btn" to="/archive">동아리 둘러보기</RouterLink>
          <RouterLink class="btn ghost" to="/me">내 정보</RouterLink>
        </div>
      </template>

      <template v-else>
        <p v-if="resent" class="privacy">
          인증 메일을 다시 보냈습니다. 받은편지함을 확인해주세요.
        </p>
        <form v-else @submit.prevent="resend">
          <div class="fld">
            <label for="email">가입한 학교 이메일</label>
            <input id="email" v-model="email" type="email"
                   placeholder="2022261026@mjc.ac.kr" required>
          </div>
          <p v-if="error" class="warn">{{ error }}</p>
          <button class="btn wide" type="submit">인증 메일 다시 받기</button>
        </form>
      </template>
    </div>
  </div>
</template>

<style scoped>
.narrow { width: min(480px, calc(100vw - 40px)); padding: clamp(48px, 9vh, 96px) 0 90px; }
.top { margin: 10px 0 24px; font-size: 14.5px; line-height: 1.8; }
.box { padding: 22px 24px 24px; }
.box:hover { transform: none; box-shadow: 0 5px 16px var(--shadow); }
.fld { margin-bottom: 14px; }
.warn { margin: 0 0 12px; }
.wide { width: 100%; }
.row { display: flex; gap: 10px; flex-wrap: wrap; }
.row .btn { flex: 1; text-decoration: none; }
</style>
