<script setup>
/* T1 — 회원가입 (담당 wj). 명세: api.md §2 · 기획서 §4.1
 *
 * 학번이 계정 식별자다. 이메일 도메인이 둘이라 학번을 따로 받지 않고 로컬파트에서
 * 끌어온다 — 둘을 따로 받으면 EMAIL_ID_MISMATCH 를 사용자가 이해하기 어렵다.
 */
import { computed, ref } from 'vue'
import api from '../api'

const DOMAINS = ['mjc.ac.kr', 'on.mjc.ac.kr']

const studentId = ref('')
const domain = ref(DOMAINS[0])
const password = ref('')
const password2 = ref('')
const name = ref('')
const dept = ref('')
const birth = ref('')
const gender = ref('남')

const pending = ref(false)
const error = ref('')
const done = ref(null)   // {email, email_sent}

const email = computed(() => (studentId.value ? `${studentId.value}@${domain.value}` : ''))

async function submit() {
  error.value = ''
  if (password.value !== password2.value) {
    error.value = '비밀번호가 서로 다릅니다.'
    return
  }
  pending.value = true
  try {
    const r = await api.auth.signup({
      email: email.value,
      password: password.value,
      student_id: studentId.value,
      name: name.value,
      dept: dept.value,
      birth: birth.value,
      gender: gender.value,
    })
    done.value = { email: email.value, email_sent: r.email_sent }
  } catch (e) {
    error.value = e.message
  } finally {
    pending.value = false
  }
}

async function resend() {
  await api.auth.resendVerification(done.value.email)
  done.value = { ...done.value, resent: true }
}
</script>

<template>
  <div class="container narrow">
    <!-- 가입 완료 — 인증 메일 안내 -->
    <template v-if="done">
      <h1 class="page-title">거의 다 됐어요</h1>
      <p class="sub top">{{ done.email }} 로 인증 메일을 보냈습니다.</p>

      <div class="card form">
        <p class="msg">
          메일의 링크를 열면 인증이 끝납니다. 인증 전에도 둘러볼 수는 있지만,
          동아리 가입 신청과 글 작성은 인증 후에 가능합니다.
        </p>

        <p v-if="!done.email_sent" class="warn">
          메일 발송에 실패했습니다. 운영자에게 문의하거나 아래에서 다시 시도해주세요.
        </p>
        <p v-if="done.resent" class="privacy">인증 메일을 다시 보냈습니다.</p>

        <div class="row">
          <button class="btn ghost" type="button" @click="resend">인증 메일 다시 보내기</button>
          <RouterLink class="btn" to="/login">로그인하러 가기</RouterLink>
        </div>
      </div>
    </template>

    <!-- 가입 폼 -->
    <template v-else>
      <h1 class="page-title">회원가입</h1>
      <p class="sub top">명지전문대학 이메일을 쓰는 재학생만 가입할 수 있습니다.</p>

      <form class="card form" @submit.prevent="submit">
        <div class="fld">
          <label for="sid">학번<span class="req">*</span></label>
          <div class="mail">
            <input id="sid" v-model="studentId" inputmode="numeric" pattern="[0-9]+"
                   placeholder="26011234" required>
            <span class="at">@</span>
            <select v-model="domain" aria-label="이메일 도메인">
              <option v-for="d in DOMAINS" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          <p class="hint">학번이 곧 이메일 주소입니다. 도메인이 달라도 한 학번으로 한 번만 가입됩니다.</p>
        </div>

        <div class="two">
          <div class="fld">
            <label for="name">이름<span class="req">*</span></label>
            <input id="name" v-model="name" required>
          </div>
          <div class="fld">
            <label for="dept">학과<span class="req">*</span></label>
            <input id="dept" v-model="dept" placeholder="컴퓨터정보과" required>
          </div>
        </div>

        <div class="two">
          <div class="fld">
            <label for="birth">생년월일<span class="req">*</span></label>
            <input id="birth" v-model="birth" type="date" required>
          </div>
          <div class="fld">
            <label for="gender">성별<span class="req">*</span></label>
            <select id="gender" v-model="gender">
              <option value="남">남</option>
              <option value="여">여</option>
            </select>
          </div>
        </div>

        <div class="two">
          <div class="fld">
            <label for="pw">비밀번호<span class="req">*</span></label>
            <input id="pw" v-model="password" type="password" autocomplete="new-password"
                   minlength="8" required>
            <p class="hint">8자 이상</p>
          </div>
          <div class="fld">
            <label for="pw2">비밀번호 확인<span class="req">*</span></label>
            <input id="pw2" v-model="password2" type="password" autocomplete="new-password" required>
          </div>
        </div>

        <p class="privacy">
          생년월일·성별은 계정 정보로만 보관합니다. 동아리장에게는
          <b>이름 · 학과 · 학년</b>만 전달됩니다.
        </p>

        <p v-if="error" class="warn">{{ error }}</p>

        <button class="btn wide" type="submit" :disabled="pending">
          {{ pending ? '가입 중…' : '가입하기' }}
        </button>

        <p class="swap">
          이미 계정이 있나요?
          <RouterLink class="link" to="/login">로그인</RouterLink>
        </p>
      </form>
    </template>
  </div>
</template>

<style scoped>
.narrow { width: min(560px, calc(100vw - 40px)); padding: clamp(36px, 7vh, 72px) 0 90px; }
.top { margin: 8px 0 24px; }
.form { padding: 24px; }
.form:hover { transform: none; box-shadow: 0 5px 16px var(--shadow); }
.fld { margin-bottom: 16px; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }

.mail { display: flex; align-items: center; gap: 8px; }
.mail input { flex: 1; min-width: 0; }
.mail select { width: auto; flex: none; }
.at { color: var(--dim); }

.privacy { margin: 4px 0 16px; }
.warn { margin: 0 0 14px; }
.wide { width: 100%; }
.msg { margin: 0 0 16px; font-size: 14.5px; line-height: 1.8; }
.row { display: flex; gap: 10px; flex-wrap: wrap; }
.row .btn { flex: 1; text-decoration: none; }
.swap { margin: 16px 0 0; text-align: center; font-size: 13.5px; color: var(--dim); }
.swap .link { color: var(--accent); font-weight: 700; text-decoration: underline; }

@media (max-width: 560px) { .two { grid-template-columns: 1fr; } }
</style>
