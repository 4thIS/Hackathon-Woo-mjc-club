<script setup>
/* T1 + T6 — 내 정보 (담당 wj). 명세: api.md §2 · 기획서 §4.3~§4.5
 *
 * 구역: 인증 배너 · 프로필 · 비밀번호 · AI 키 · 내 동아리 · 신청 현황
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()

const clubs = ref([])
const requests = ref({ join: [], create: [], leave: [] })
const loading = ref(true)

const profile = reactive({ dept: '', academic_status: '재학' })
const profileMsg = ref('')
const profileErr = ref('')

const pw = reactive({ next: '', confirm: '' })
const pwMsg = ref('')
const pwErr = ref('')

const keyInput = ref('')
const keyBusy = ref(false)
const keyErr = ref('')

const resent = ref(false)

const me = computed(() => auth.user)
const hasKey = computed(() => !!me.value?.ai_key?.registered)
const noRequests = computed(
  () => !requests.value.join.length && !requests.value.create.length && !requests.value.leave.length,
)

onMounted(async () => {
  profile.dept = me.value?.dept ?? ''
  profile.academic_status = me.value?.academic_status ?? '재학'
  try {
    const [c, r] = await Promise.all([api.me.clubs(), api.me.requests()])
    clubs.value = c
    requests.value = r
  } finally {
    loading.value = false
  }
})

async function saveProfile() {
  profileMsg.value = ''
  profileErr.value = ''
  try {
    auth.user = await api.me.update({
      dept: profile.dept,
      academic_status: profile.academic_status,
    })
    profileMsg.value = '저장했습니다.'
    clubs.value = await api.me.clubs()   // 졸업 전환이면 멤버십이 OB 로 바뀐다
  } catch (e) {
    // 동아리장이면 졸업할 수 없다 (기획서 §4.3) — 화면 값도 원래대로 되돌린다
    profileErr.value = e.message
    profile.academic_status = me.value?.academic_status ?? '재학'
  }
}

async function savePassword() {
  pwMsg.value = ''
  pwErr.value = ''
  if (pw.next !== pw.confirm) {
    pwErr.value = '새 비밀번호가 서로 다릅니다.'
    return
  }
  try {
    await api.me.update({ password: pw.next })
    pw.next = ''
    pw.confirm = ''
    pwMsg.value = '비밀번호를 바꿨습니다.'
  } catch (e) {
    pwErr.value = e.message
  }
}

async function saveKey() {
  keyErr.value = ''
  keyBusy.value = true
  try {
    // 저장 전에 서버가 게이트웨이로 유효성을 확인한다 (기획서 §4.5)
    const r = await api.me.registerAiKey(keyInput.value.trim())
    auth.user = { ...me.value, ai_key: r }
    keyInput.value = ''
  } catch (e) {
    keyErr.value = e.message
  } finally {
    keyBusy.value = false
  }
}

async function removeKey() {
  keyErr.value = ''
  keyBusy.value = true
  try {
    await api.me.deleteAiKey()
    auth.user = { ...me.value, ai_key: { registered: false, masked: null } }
  } catch (e) {
    keyErr.value = e.message
  } finally {
    keyBusy.value = false
  }
}

async function resendVerification() {
  await api.auth.resendVerification(me.value.email)
  resent.value = true
}

async function cancelRequest(kind, id) {
  if (kind === 'join') await api.joinRequests.cancel(id)
  else await api.clubApplications.cancel(id)
  requests.value = await api.me.requests()
}

function dday(iso) {
  const days = Math.ceil((new Date(iso) - Date.now()) / 86400000)
  return days > 0 ? `D-${days}` : '곧'
}

/* ── 회원 탈퇴 ── */
const wdDlg = ref(null)
const wdPassword = ref('')
const wdConfirm = ref('')
const wdBusy = ref(false)
const wdErr = ref('')

const CONFIRM_WORD = '탈퇴합니다'
const leaderClubs = computed(() => clubs.value.filter((m) => m.role === '동아리장'))
const canWithdraw = computed(
  () => wdPassword.value && wdConfirm.value.trim() === CONFIRM_WORD && !leaderClubs.value.length,
)

function openWithdraw() {
  wdPassword.value = ''
  wdConfirm.value = ''
  wdErr.value = ''
  wdDlg.value?.showModal()
}

async function withdraw() {
  if (!canWithdraw.value) return
  wdErr.value = ''
  wdBusy.value = true
  try {
    await api.me.withdraw(wdPassword.value)
    auth.user = null
    wdDlg.value?.close()
    router.replace('/')
  } catch (e) {
    wdErr.value = e.message
  } finally {
    wdBusy.value = false
  }
}
</script>

<template>
  <div v-if="me" class="container page">
    <h1 class="page-title">내 정보</h1>
    <p class="sub top">{{ me.name }} · {{ me.dept }} · {{ me.grade }}학년 · {{ me.email }}</p>

    <!-- 미인증 안내 (기획서 §4.2) -->
    <p v-if="!me.email_verified" class="warn banner">
      <template v-if="resent">인증 메일을 다시 보냈습니다. 받은편지함을 확인해주세요.</template>
      <template v-else>
        이메일 인증 전에는 가입 신청과 글 작성을 할 수 없습니다.
        <button class="linkbtn" type="button" @click="resendVerification">인증 메일 다시 받기</button>
      </template>
    </p>

    <div class="grid">
      <!-- ── 프로필 ── -->
      <section class="card sec">
        <h2 class="section-title">프로필</h2>
        <p class="hint">전과·휴학은 직접 고칠 수 있습니다. 이름·학번·생년월일·성별은 잠겨 있습니다.</p>

        <form class="body" @submit.prevent="saveProfile">
          <div class="fld">
            <label for="dept">학과</label>
            <input id="dept" v-model="profile.dept">
          </div>
          <div class="fld">
            <label for="status">학적 상태</label>
            <select id="status" v-model="profile.academic_status">
              <option value="재학">재학</option>
              <option value="휴학">휴학</option>
              <option value="졸업">졸업</option>
            </select>
            <p class="hint">졸업으로 바꾸면 모든 동아리 소속이 OB 가 됩니다.</p>
          </div>

          <p v-if="profileErr" class="warn">{{ profileErr }}</p>
          <p v-else-if="profileMsg" class="privacy">{{ profileMsg }}</p>

          <button class="btn" type="submit">저장</button>
        </form>
      </section>

      <!-- ── 비밀번호 ── -->
      <section class="card sec">
        <h2 class="section-title">비밀번호 변경</h2>
        <p class="hint">바꾸면 다음 로그인부터 새 비밀번호를 씁니다.</p>

        <form class="body" @submit.prevent="savePassword">
          <div class="fld">
            <label for="pw1">새 비밀번호</label>
            <input id="pw1" v-model="pw.next" type="password" autocomplete="new-password" minlength="8">
            <p class="hint">8자 이상</p>
          </div>
          <div class="fld">
            <label for="pw2">새 비밀번호 확인</label>
            <input id="pw2" v-model="pw.confirm" type="password" autocomplete="new-password">
          </div>

          <p v-if="pwErr" class="warn">{{ pwErr }}</p>
          <p v-else-if="pwMsg" class="privacy">{{ pwMsg }}</p>

          <button class="btn" type="submit" :disabled="!pw.next">변경</button>
        </form>
      </section>

      <!-- ── AI 키 (기획서 §4.5) ── -->
      <section class="card sec wide">
        <h2 class="section-title">AI API 키</h2>
        <p class="hint">
          활동 글 초안은 <b>본인이 발급받은 키</b>로 만듭니다. 서비스가 공용 키로 대신 부르지 않습니다.
        </p>

        <div class="body">
          <template v-if="hasKey">
            <div class="keyrow">
              <code class="masked">{{ me.ai_key.masked }}</code>
              <span class="chip">등록됨</span>
              <button class="btn ghost" type="button" :disabled="keyBusy" @click="removeKey">삭제</button>
            </div>
            <p class="privacy">
              저장된 키는 암호화되어 있고 <b>다시 볼 수 없습니다.</b> 바꾸려면 지우고 새로 넣어주세요.
            </p>
          </template>

          <template v-else>
            <ol class="steps">
              <li>
                <a class="link" href="https://docs.mindlogic.ai" target="_blank" rel="noopener">
                  명지전문대학 AI</a> 에 로그인합니다.
              </li>
              <li>좌측 하단 <b>API Gateway</b> 를 엽니다.</li>
              <li><b>API 키 생성</b> 을 누르고 발급된 키를 붙여넣습니다.</li>
            </ol>
            <form class="keyrow" @submit.prevent="saveKey">
              <input v-model="keyInput" type="password" autocomplete="off"
                     placeholder="발급받은 키를 붙여넣으세요">
              <button class="btn" type="submit" :disabled="keyBusy || !keyInput">
                {{ keyBusy ? '확인 중…' : '등록' }}
              </button>
            </form>
            <p class="hint">등록 전에 실제로 쓸 수 있는 키인지 한 번 확인합니다.</p>
          </template>

          <p v-if="keyErr" class="warn keyerr">{{ keyErr }}</p>
        </div>
      </section>

      <!-- ── 내 동아리 ── -->
      <section class="card sec wide">
        <h2 class="section-title">내 동아리</h2>
        <div class="body">
          <p v-if="loading" class="hint">불러오는 중…</p>
          <p v-else-if="!clubs.length" class="empty">
            아직 가입한 동아리가 없어요.
            <RouterLink class="link" to="/archive">둘러보기</RouterLink>
          </p>
          <ul v-else class="list">
            <li v-for="m in clubs" :key="m.club.id">
              <RouterLink class="nm" :to="`/clubs/${m.club.id}`">{{ m.club.name }}</RouterLink>
              <span class="chip">{{ m.role }}</span>
              <span v-if="m.membership === 'OB'" class="chip ob">OB</span>
              <span v-if="m.gen" class="meta">{{ m.gen }}기</span>
              <RouterLink v-if="m.role === '동아리장'" class="manage" :to="`/clubs/${m.club.id}/manage`">
                관리
              </RouterLink>
            </li>
          </ul>
        </div>
      </section>

      <!-- ── 신청 현황 (기획서 §4.4) ── -->
      <section class="card sec wide">
        <h2 class="section-title">내 신청 현황</h2>
        <div class="body">
          <p v-if="loading" class="hint">불러오는 중…</p>
          <p v-else-if="noRequests" class="empty">아직 신청한 게 없어요.</p>

          <template v-else>
            <div v-if="requests.join.length" class="grp">
              <p class="k">동아리 가입</p>
              <ul class="list">
                <li v-for="r in requests.join" :key="r.id">
                  <span class="nm">{{ r.club_name }}</span>
                  <span class="chip">{{ r.status }}</span>
                  <button v-if="r.cancellable" class="linkbtn" type="button"
                          @click="cancelRequest('join', r.id)">신청 취소</button>
                </li>
              </ul>
            </div>

            <div v-if="requests.create.length" class="grp">
              <p class="k">동아리 개설</p>
              <ul class="list">
                <li v-for="r in requests.create" :key="r.id">
                  <span class="nm">{{ r.name }}</span>
                  <span class="chip">{{ r.status }}</span>
                  <span v-if="r.reject_reason" class="meta">{{ r.reject_reason }}</span>
                  <button v-if="r.cancellable" class="linkbtn" type="button"
                          @click="cancelRequest('create', r.id)">신청 취소</button>
                </li>
              </ul>
            </div>

            <div v-if="requests.leave.length" class="grp">
              <p class="k">탈퇴 요청</p>
              <ul class="list">
                <li v-for="r in requests.leave" :key="r.id">
                  <span class="nm">{{ r.club_name }}</span>
                  <span class="chip">{{ r.status }}</span>
                  <!-- 동아리장이 응답하지 않아도 7일 뒤 자동 처리된다 (기획서 §5.4) -->
                  <span v-if="r.status === '심사중'" class="meta">
                    {{ dday(r.auto_approve_at) }} 자동 승인
                  </span>
                </li>
              </ul>
            </div>
          </template>
        </div>
      </section>

      <!-- ── 회원 탈퇴 ── -->
      <section class="card sec wide danger">
        <h2 class="section-title">회원 탈퇴</h2>
        <p class="hint">
          계정과 동아리 소속·신청 이력이 지워집니다. <b>되돌릴 수 없습니다.</b><br>
          다만 작성한 <b>활동 글은 동아리에 남습니다</b> — 기록은 동아리의 자산이라 지우지 않습니다.
        </p>
        <div class="body">
          <p v-if="leaderClubs.length" class="warn">
            {{ leaderClubs.map((m) => m.club.name).join(' · ') }} 의 동아리장입니다.
            먼저 동아리장을 위임해야 탈퇴할 수 있습니다.
          </p>
          <button class="btn ghost danger-btn" type="button"
                  :disabled="!!leaderClubs.length" @click="openWithdraw">
            회원 탈퇴
          </button>
        </div>
      </section>
    </div>

    <!-- 탈퇴 확인 모달 (디자인 기획 §6-2) -->
    <dialog ref="wdDlg" class="narrow" @click.self="wdDlg.close()">
      <div class="sheet-hd">
        <h2>정말 탈퇴하시겠어요?</h2>
        <p>되돌릴 수 없습니다.</p>
        <button class="x" aria-label="닫기" @click="wdDlg.close()">✕</button>
      </div>

      <form class="sheet-bd" @submit.prevent="withdraw">
        <div class="fld">
          <label for="wd-pw">비밀번호</label>
          <input id="wd-pw" v-model="wdPassword" type="password" autocomplete="current-password">
        </div>
        <div class="fld">
          <label for="wd-cf">확인을 위해 <b>{{ CONFIRM_WORD }}</b> 를 입력해주세요</label>
          <input id="wd-cf" v-model="wdConfirm" :placeholder="CONFIRM_WORD" autocomplete="off">
        </div>
        <p v-if="wdErr" class="warn">{{ wdErr }}</p>
        <button class="hidden-submit" type="submit" tabindex="-1" aria-hidden="true"></button>
      </form>

      <div class="sheet-ft">
        <button class="btn ghost" type="button" @click="wdDlg.close()">취소</button>
        <button class="btn danger-btn" type="button" :disabled="!canWithdraw || wdBusy"
                @click="withdraw">
          {{ wdBusy ? '처리 중…' : '탈퇴하기' }}
        </button>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
.page { padding: clamp(32px, 6vh, 64px) 0 100px; }
.top { margin: 8px 0 20px; }
.banner { margin: 0 0 20px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
.sec { padding: 20px 22px 22px; }
.sec:hover { transform: none; box-shadow: 0 5px 16px var(--shadow); }
.sec.wide { grid-column: 1 / -1; }
.sec > .hint { margin-top: 6px; }
.body { margin-top: 16px; }
.fld { margin-bottom: 14px; }
.warn, .privacy { margin: 0 0 14px; }
.keyerr { margin: 14px 0 0; }

.keyrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.keyrow input { flex: 1; min-width: 220px; }
.masked { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 15px; letter-spacing: .06em; }

.steps { margin: 0 0 14px; padding-left: 20px; font-size: 13.5px; line-height: 1.9; color: var(--dim); }
.steps b { color: var(--ink); }

.list { list-style: none; margin: 0; padding: 0; }
.list li {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 11px 0; border-bottom: 1px solid var(--line); font-size: 14px;
}
.list li:last-child { border-bottom: none; }
.nm { font-weight: 700; text-decoration: none; color: var(--ink); }
a.nm:hover { color: var(--accent); }
.chip.ob { background: transparent; border: 1.5px solid var(--line); color: var(--dim); }
.meta { font-size: 12.5px; color: var(--dim); }
.manage { margin-left: auto; font-size: 13px; font-weight: 700; color: var(--accent); }

.grp + .grp { margin-top: 18px; }
.k { font-size: 11px; font-weight: 700; letter-spacing: .13em; color: var(--dim); margin: 0 0 4px; }
.empty { font-size: 14px; color: var(--dim); margin: 0; }
.link { color: var(--accent); font-weight: 700; }
.linkbtn {
  background: none; border: none; padding: 0; cursor: pointer;
  color: var(--accent); font: inherit; font-size: 13px; font-weight: 700; text-decoration: underline;
}

/* 파괴적 동작은 눈에 띄되 실수로 눌리지 않게 — 테두리만 경고색, 채움은 아님 */
.sec.danger { border-color: var(--warnLine); }
.danger-btn { border-color: var(--warnLine); color: var(--warnInk); }
.btn.danger-btn:not(.ghost) { background: var(--warnInk); color: var(--card); border-color: var(--warnInk); }

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
.hidden-submit { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }

@media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
</style>
