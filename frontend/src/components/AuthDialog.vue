<script setup>
/* 로그인·회원가입 모달 — 디자인 기획 §6-2 ("모달은 전부 <dialog> — 로그인/회원가입/위임 포함")
 *
 * 둘을 한 모달의 탭으로 둔다. 보던 화면을 벗어나지 않아야 동아리를 보다가
 * 가입 버튼을 눌렀을 때 흐름이 끊기지 않는다.
 */
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { useAuth } from '../stores/auth'
import { CONSENTS } from '../content/terms'

const auth = useAuth()
const route = useRoute()
const router = useRouter()

const DOMAINS = ['mjc.ac.kr', 'on.mjc.ac.kr']

const dlg = ref(null)
const tab = ref('login')          // login | signup
const pending = ref(false)
const error = ref('')
const done = ref(null)            // 가입 완료 후 인증 안내 {email, email_sent, resent}

const login = reactive({ email: '', password: '' })
const su = reactive({
  studentId: '', mailLocal: '', domain: DOMAINS[0], password: '', password2: '',
  name: '', dept: '', grade: 1, birth: '', gender: '남',
})

/* 약관 동의 — 둘 다 필수다. 하나라도 빠지면 가입 버튼이 잠긴다 */
const agreed = reactive(Object.fromEntries(CONSENTS.map((c) => [c.key, false])))
const allAgreed = computed(() => CONSENTS.every((c) => agreed[c.key]))
const someAgreed = computed(() => CONSENTS.some((c) => agreed[c.key]))

function toggleAll(on) {
  CONSENTS.forEach((c) => { agreed[c.key] = on })
}

/* 학번과 메일 주소는 별개다 — 학번이 곧 주소인 계정이 많을 뿐이라
 * 메일 칸을 비워두면 학번으로 채워준다. */
const suEmail = computed(() => {
  const local = su.mailLocal.trim() || su.studentId
  return local ? `${local}@${su.domain}` : ''
})

function open(which = 'login') {
  tab.value = which
  error.value = ''
  done.value = null
  if (!dlg.value?.open) dlg.value?.showModal()
}
defineExpose({ open })

/** 닫히면 주소창의 ?auth= · ?next= 를 치운다. 새로고침 때 다시 열리면 안 된다. */
function clearQuery() {
  if (!route.query.auth && !route.query.next) return
  const { auth: _a, next: _n, ...rest } = route.query
  router.replace({ path: route.path, query: rest })
}

function close() {
  dlg.value?.close()
}

function switchTo(next) {
  tab.value = next
  error.value = ''
}

async function submitLogin() {
  error.value = ''
  pending.value = true
  try {
    await auth.login(login.email.trim(), login.password)
    login.password = ''
    dlg.value?.close()
    // 가드가 붙여 보낸 원래 목적지로 돌려보낸다
    const next = route.query.next
    if (typeof next === 'string' && next) router.replace(next)
  } catch (e) {
    error.value = e.message
  } finally {
    pending.value = false
  }
}

async function submitSignup() {
  error.value = ''
  if (su.password !== su.password2) {
    error.value = '비밀번호가 서로 다릅니다.'
    return
  }
  if (!allAgreed.value) {
    error.value = '이용약관과 개인정보 수집·이용에 동의해야 가입할 수 있습니다.'
    return
  }
  pending.value = true
  try {
    const r = await api.auth.signup({
      email: suEmail.value,
      password: su.password,
      student_id: su.studentId,
      name: su.name,
      dept: su.dept,
      grade: Number(su.grade),
      birth: su.birth,
      gender: su.gender,
    })
    done.value = { email: suEmail.value, email_sent: r.email_sent }
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
  <dialog ref="dlg" :class="{ narrow: tab === 'login' && !done }"
          @click.self="close()" @close="clearQuery()">
    <!-- 가입 완료 — 인증 안내 -->
    <template v-if="done">
      <div class="sheet-hd">
        <h2>거의 다 됐어요</h2>
        <p>{{ done.email }} 로 인증 메일을 보냈습니다.</p>
        <button class="x" aria-label="닫기" @click="close()">✕</button>
      </div>
      <div class="sheet-bd">
        <p class="msg">
          메일의 링크를 열면 인증이 끝납니다. 인증 전에도 둘러볼 수는 있지만,
          동아리 가입 신청과 글 작성은 인증 후에 가능합니다.
        </p>
        <p v-if="!done.email_sent" class="warn">
          메일 발송에 실패했습니다. 아래에서 다시 시도하거나 운영자에게 문의해주세요.
        </p>
        <p v-if="done.resent" class="privacy">인증 메일을 다시 보냈습니다.</p>
      </div>
      <div class="sheet-ft">
        <button class="btn ghost" @click="resend">인증 메일 다시 보내기</button>
        <button class="btn" @click="switchTo('login'); done = null">로그인하기</button>
      </div>
    </template>

    <!-- 로그인 · 회원가입 -->
    <template v-else>
      <div class="sheet-hd">
        <h2>{{ tab === 'login' ? '로그인' : '회원가입' }}</h2>
        <p>
          {{ tab === 'login'
            ? '학교 이메일로 로그인합니다.'
            : '명지전문대학 이메일을 쓰는 재학생만 가입할 수 있습니다.' }}
        </p>
        <button class="x" aria-label="닫기" @click="close()">✕</button>
      </div>

      <form class="sheet-bd" @submit.prevent="tab === 'login' ? submitLogin() : submitSignup()">
        <!-- 로그인 -->
        <template v-if="tab === 'login'">
          <div class="fld">
            <label for="li-email">학교 이메일</label>
            <input id="li-email" v-model="login.email" type="email" autocomplete="username"
                   placeholder="2022261026@mjc.ac.kr" required>
          </div>
          <div class="fld">
            <label for="li-pw">비밀번호</label>
            <input id="li-pw" v-model="login.password" type="password"
                   autocomplete="current-password" required>
          </div>
        </template>

        <!-- 회원가입 -->
        <template v-else>
          <div class="fld">
            <label for="su-sid">학번<span class="req">*</span></label>
            <input id="su-sid" v-model="su.studentId" inputmode="numeric" pattern="[0-9]{10}"
                   maxlength="10" placeholder="2022261026" required>
            <p class="hint">10자리 숫자입니다. 계정 식별자라 가입 후에는 바꿀 수 없습니다.</p>
          </div>

          <div class="fld">
            <label for="su-mail">학교 이메일<span class="req">*</span></label>
            <div class="mail">
              <input id="su-mail" v-model="su.mailLocal" autocomplete="username"
                     :placeholder="su.studentId || '2022261026'">
              <span class="at">@</span>
              <select v-model="su.domain" aria-label="이메일 도메인">
                <option v-for="d in DOMAINS" :key="d" :value="d">{{ d }}</option>
              </select>
            </div>
            <p class="hint">
              로그인에 쓰는 주소입니다. 비워두면 학번으로 만듭니다 —
              주소가 학번과 달라도 됩니다.
            </p>
          </div>

          <div class="fld">
            <label for="su-name">이름<span class="req">*</span></label>
            <input id="su-name" v-model="su.name" required>
          </div>

          <div class="two">
            <div class="fld">
              <label for="su-dept">학과<span class="req">*</span></label>
              <input id="su-dept" v-model="su.dept" placeholder="컴퓨터정보과" required>
            </div>
            <div class="fld">
              <label for="su-grade">학년<span class="req">*</span></label>
              <select id="su-grade" v-model="su.grade">
                <option :value="1">1학년</option>
                <option :value="2">2학년</option>
                <option :value="3">3학년</option>
                <option :value="4">4학년</option>
              </select>
            </div>
          </div>

          <div class="two">
            <div class="fld">
              <label for="su-birth">생년월일<span class="req">*</span></label>
              <input id="su-birth" v-model="su.birth" type="date" required>
            </div>
            <div class="fld">
              <label for="su-gender">성별<span class="req">*</span></label>
              <select id="su-gender" v-model="su.gender">
                <option value="남">남</option>
                <option value="여">여</option>
              </select>
            </div>
          </div>

          <div class="two">
            <div class="fld">
              <label for="su-pw">비밀번호<span class="req">*</span></label>
              <input id="su-pw" v-model="su.password" type="password" autocomplete="new-password"
                     minlength="8" required>
              <p class="hint">8자 이상</p>
            </div>
            <div class="fld">
              <label for="su-pw2">비밀번호 확인<span class="req">*</span></label>
              <input id="su-pw2" v-model="su.password2" type="password"
                     autocomplete="new-password" required>
            </div>
          </div>

          <p class="privacy">
            <span>🔒</span>
            <span>생년월일·성별은 계정 정보로만 보관합니다. 동아리장에게는
              <b>이름 · 학과 · 학년</b>만 전달됩니다.</span>
          </p>

          <!-- 약관 동의 — 둘 다 필수. 각 항목은 접힌 채로 두고 눌러서 요약을 본다 -->
          <div class="terms">
            <label class="all">
              <input type="checkbox" :checked="allAgreed"
                     :indeterminate.prop="someAgreed && !allAgreed"
                     @change="toggleAll($event.target.checked)">
              <b>약관에 모두 동의합니다</b>
            </label>

            <div v-for="c in CONSENTS" :key="c.key" class="item">
              <label class="one">
                <input v-model="agreed[c.key]" type="checkbox">
                <span>{{ c.label }}</span>
                <em class="req-tag">필수</em>
              </label>

              <details class="brief">
                <summary>내용 보기</summary>
                <ul>
                  <li v-for="(line, i) in c.brief" :key="i">{{ line }}</li>
                </ul>
                <RouterLink class="full" :to="`/terms#${c.docId}`" @click="close()">
                  전문 보기 →
                </RouterLink>
              </details>
            </div>
          </div>
        </template>

        <p v-if="error" class="warn err">{{ error }}</p>

        <button class="hidden-submit" type="submit" tabindex="-1" aria-hidden="true"></button>
      </form>

      <div class="sheet-ft">
        <button class="btn ghost" type="button"
                @click="switchTo(tab === 'login' ? 'signup' : 'login')">
          {{ tab === 'login' ? '회원가입' : '로그인' }}
        </button>
        <button class="btn" type="button"
                :disabled="pending || (tab === 'signup' && !allAgreed)"
                :title="tab === 'signup' && !allAgreed ? '약관에 동의해야 가입할 수 있습니다' : ''"
                @click="tab === 'login' ? submitLogin() : submitSignup()">
          {{ pending ? '확인 중…' : (tab === 'login' ? '로그인' : '가입하기') }}
        </button>
      </div>
    </template>
  </dialog>
</template>

<style scoped>
dialog { max-height: min(86vh, 760px); overflow: auto; box-shadow: 0 26px 70px var(--shadowUp); }
dialog::backdrop { backdrop-filter: blur(3px); }

.sheet-hd {
  position: sticky; top: 0; z-index: 2; background: var(--card);
  padding: 22px 24px 14px; border-bottom: 1px solid var(--line);
}
.sheet-hd h2 { margin: 0 0 4px; font-size: 19px; letter-spacing: -.025em; }
.sheet-hd p { margin: 0; font-size: 13px; color: var(--dim); }
.sheet-hd .x {
  position: absolute; top: 16px; right: 16px; width: 32px; height: 32px;
  border: none; border-radius: 9px; background: none; color: var(--dim);
  font-size: 16px; cursor: pointer;
}
.sheet-hd .x:hover { background: var(--chip); color: var(--ink); }

.sheet-bd { padding: 20px 24px 4px; }
.sheet-ft { display: flex; gap: 9px; padding: 16px 24px 24px; }
.sheet-ft .btn { flex: 1; }

.fld { margin-bottom: 14px; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.mail { display: flex; align-items: center; gap: 8px; }
.mail input { flex: 1; min-width: 0; }
.mail select { width: auto; flex: none; }
.at { color: var(--dim); }

.privacy { display: flex; gap: 9px; align-items: flex-start; margin: 4px 0 14px; }
.err { margin: 0 0 14px; }
.msg { margin: 0 0 14px; font-size: 14.5px; line-height: 1.8; }
.warn, .privacy { margin-bottom: 14px; }

/* Enter 로 제출되게만 두고 화면에는 보이지 않는다 (버튼은 sheet-ft 에 있다) */
.hidden-submit { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }

/* --- 약관 동의 --- */
.terms {
  border: var(--border); border-radius: var(--r-input);
  padding: 12px 14px; margin-top: 2px;
}
.terms label { display: flex; align-items: center; gap: 9px; margin: 0; font-weight: 400; }
.terms input[type="checkbox"] {
  width: 16px; height: 16px; flex: none; margin: 0; padding: 0;
  accent-color: var(--accent); cursor: pointer;
}
.terms .all { padding-bottom: 11px; border-bottom: 1px solid var(--line); font-size: 14px; }
.terms .all b { font-weight: 700; letter-spacing: -.015em; }

.item { padding-top: 11px; }
.one { font-size: 13.5px; cursor: pointer; }
.req-tag {
  font-style: normal; margin-left: auto; flex: none;
  font-size: 11px; font-weight: 700; color: var(--accent);
}

/* 작은 글씨 요약 — 접힌 채로 두고 눌러서 편다 */
.brief { margin: 6px 0 0 25px; }
.brief summary {
  display: inline-block; list-style: none; cursor: pointer;
  font-size: 12px; font-weight: 700; color: var(--dim);
  text-decoration: underline; text-underline-offset: 3px;
}
.brief summary::-webkit-details-marker { display: none; }
.brief summary:hover { color: var(--accent); }
.brief[open] summary { margin-bottom: 7px; }
.brief ul {
  margin: 0; padding: 10px 12px; list-style: none;
  background: var(--chip); border-radius: 10px;
  display: flex; flex-direction: column; gap: 7px;
}
.brief li {
  font-size: 11.5px; line-height: 1.7; color: var(--dim);
  padding-left: 11px; position: relative;
}
.brief li::before {
  content: ""; position: absolute; left: 0; top: .68em;
  width: 3px; height: 3px; border-radius: 50%; background: var(--dim); opacity: .6;
}
.brief .full {
  display: inline-block; margin-top: 7px;
  font-size: 11.5px; font-weight: 700; color: var(--accent);
}
.brief .full:hover { text-decoration: underline; }

@media (max-width: 560px) { .two { grid-template-columns: 1fr; } }
</style>
