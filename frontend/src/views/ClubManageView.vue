<script setup>
/* 동아리 관리 — 명세: docs/api.md §4
 * 가입폼 편집 · 신청자 승인/거절 · 부원 관리(기수/위임) · 탈퇴 요청 승인 · 동아리 정보 수정
 */
import { computed, onMounted, reactive, ref } from 'vue'
import api, { ApiError } from '../api'
import { gradeLabel } from '../content/grade'

const props = defineProps({ id: { type: String, required: true } })
const clubId = computed(() => Number(props.id))

const club = ref(null)
const joinRequests = ref([])
const members = ref([])
const leaveRequests = ref([])
const formDraft = reactive({ required: false, fields: [] })
const clubEdit = reactive({
  purpose: '', meet_day: '', meet_time: '', meet_place: '', recruit_status: '모집중', current_gen: null,
})

const loading = ref(true)
const forbidden = ref(false)
const message = ref('')
const messageIsError = ref(false)

/* 저장 결과는 팝업(모달)으로 알린다 — 인라인 메시지는 폼 아래에 있어 놓치기 쉽다 */
const resultDlg = ref(null)
const result = reactive({ ok: true, title: '', detail: '' })

function popup(title, detail = '', ok = true) {
  Object.assign(result, { ok, title, detail })
  resultDlg.value?.showModal()
}

function flash(text, isError = false) {
  message.value = text
  messageIsError.value = isError
  setTimeout(() => { if (message.value === text) message.value = '' }, 3500)
}

/* 저장된 상태의 사본. 이것과 다를 때만 저장 버튼이 열린다 */
const savedClub = ref('')
const savedForm = ref('')

const snap = (o) => JSON.stringify(o)
const clubDirty = computed(() => snap(clubEdit) !== savedClub.value)
const formDirty = computed(() => snap(formDraft) !== savedForm.value)

async function loadAll() {
  loading.value = true
  try {
    const [c, form, reqs, mem, leaves] = await Promise.all([
      api.clubs.detail(clubId.value),
      api.joinForm.get(clubId.value),
      api.joinRequests.listForClub(clubId.value),
      api.clubs.manageMembers(clubId.value),
      api.leaveRequests.listForClub(clubId.value),
    ])
    club.value = c
    formDraft.required = form.required
    formDraft.fields = normalizeKeys(form.fields)
    joinRequests.value = reqs
    members.value = mem
    leaveRequests.value = leaves
    clubEdit.purpose = c.purpose ?? ''
    clubEdit.meet_day = c.meet_day ?? ''
    clubEdit.meet_time = c.meet_time ?? ''
    clubEdit.meet_place = c.meet_place ?? ''
    clubEdit.recruit_status = c.recruit_status
    clubEdit.current_gen = c.current_gen
    savedClub.value = snap(clubEdit)
    savedForm.value = snap(formDraft)
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) forbidden.value = true
    else flash(e.message, true)
  } finally {
    loading.value = false
  }
}
onMounted(loadAll)

// --- 가입 신청 -----------------------------------------------------

const rejectDialog = ref(null)
const rejectTarget = ref(null)
const rejectReason = ref('')

async function approveRequest(req) {
  try {
    const res = await api.joinRequests.approve(req.id)
    joinRequests.value = joinRequests.value.filter((r) => r.id !== req.id)
    flash(`${req.name}님 승인 완료 (${res.gen ? res.gen + '기' : '기수 없음'})`)
    members.value = await api.clubs.manageMembers(clubId.value)
  } catch (e) {
    flash(e.message, true)
  }
}

function openReject(req) {
  rejectTarget.value = req
  rejectReason.value = ''
  rejectDialog.value.showModal()
}

async function confirmReject() {
  try {
    await api.joinRequests.reject(rejectTarget.value.id, rejectReason.value || undefined)
    joinRequests.value = joinRequests.value.filter((r) => r.id !== rejectTarget.value.id)
    rejectDialog.value.close()
    flash('거절 처리했습니다.')
  } catch (e) {
    flash(e.message, true)
  }
}

// --- 가입폼 --------------------------------------------------------

/* key 는 답변 JSON 의 키다. 화면에 보이는 글은 '질문'(label)이 맡으므로 사람이 정할
   이유가 없다. 한글이나 공백이 들어가면 답변을 다룰 때 깨지므로 자동으로 붙인다. */
const KEY_RE = /^[a-zA-Z][a-zA-Z0-9_]{0,29}$/

function nextKey() {
  const used = new Set(formDraft.fields.map((f) => f.key))
  let n = formDraft.fields.length + 1
  while (used.has(`q${n}`)) n += 1
  return `q${n}`
}

/* 예전에 손으로 넣은 한글 key 가 남아 있을 수 있다 — 불러올 때 조용히 고친다 */
function normalizeKeys(fields) {
  const out = []
  for (const f of fields) {
    const ok = KEY_RE.test((f.key ?? '').trim())
    out.push({ ...f, key: ok ? f.key.trim() : `q${out.length + 1}` })
  }
  return out
}

/* 답변은 key 로 저장된다. 동아리장에게는 질문 문구로 보여준다 —
   'q1: 짱' 은 읽을 수 없다. 폼이 바뀌어 없어진 질문이면 key 를 그대로 쓴다 */
const questionOf = computed(() => {
  const map = {}
  for (const f of formDraft.fields) map[f.key] = f.label?.trim() || f.key
  return map
})

function addField() {
  formDraft.fields.push({ key: nextKey(), label: '', type: 'text', required: false })
}
function removeField(i) {
  formDraft.fields.splice(i, 1)
}

async function saveForm() {
  formDraft.fields = normalizeKeys(formDraft.fields)
  try {
    const saved = await api.joinForm.put(clubId.value, formDraft)
    formDraft.required = saved.required
    formDraft.fields = saved.fields
    savedForm.value = snap(formDraft)
    popup('가입폼을 저장했습니다',
      saved.fields.length
        ? `질문 ${saved.fields.length}개 · ${saved.required ? '작성 필수' : '작성 선택'}`
        : '질문이 없어 신청자는 바로 신청합니다.')
  } catch (e) {
    popup('가입폼을 저장하지 못했습니다', e.message, false)
  }
}

// --- 부원 관리 -------------------------------------------------------

async function updateGen(m) {
  try {
    await api.clubs.updateMember(clubId.value, m.user.id, { gen: m.gen === '' ? null : Number(m.gen) })
    flash(`${m.user.name}님을 ${m.gen ? m.gen + '기' : '기수 없음'}로 바꿨습니다.`)
  } catch (e) {
    flash(e.message, true)
  }
}

/* 동아리 안에서의 상태. 학적(재학·휴학·졸업)은 사람 전역 값이라 여기서 못 바꾼다
   — 동아리장이 바꾸면 그 사람의 다른 동아리까지 영향을 받는다 (기획서 §3.1) */
async function updateMembership(m) {
  try {
    const r = await api.clubs.updateMember(clubId.value, m.user.id, { membership: m.membership })
    m.membership = r.membership
    flash(`${m.user.name}님을 ${r.membership}으로 바꿨습니다.`)
  } catch (e) {
    m.membership = m.membership === 'OB' ? '활동중' : 'OB'   // 되돌린다
    popup('상태를 바꾸지 못했습니다', e.message, false)
  }
}

const removeDialog = ref(null)
const removeTarget = ref(null)

function openRemove(m) {
  removeTarget.value = m
  removeDialog.value?.showModal()
}

async function confirmRemove() {
  const m = removeTarget.value
  try {
    await api.clubs.removeMember(clubId.value, m.user.id)
    removeDialog.value?.close()
    members.value = members.value.filter((x) => x.user.id !== m.user.id)
    leaveRequests.value = await api.leaveRequests.listForClub(clubId.value)
    popup('부원을 내보냈습니다', `${m.user.name}님이 동아리에서 제외되었습니다.`)
  } catch (e) {
    removeDialog.value?.close()
    popup('내보내지 못했습니다', e.message, false)
  }
}

const transferDialog = ref(null)
const transferTarget = ref(null)

function openTransfer(m) {
  transferTarget.value = m
  transferDialog.value.showModal()
}
async function confirmTransfer() {
  try {
    await api.clubs.transfer(clubId.value, transferTarget.value.user.id)
    transferDialog.value.close()
    flash(`${transferTarget.value.user.name}님에게 동아리장을 위임했습니다.`)
    members.value = await api.clubs.manageMembers(clubId.value)
  } catch (e) {
    flash(e.message, true)
  }
}

// --- 탈퇴 ------------------------------------------------------------

async function approveLeave(req) {
  try {
    await api.leaveRequests.approve(req.id)
    leaveRequests.value = leaveRequests.value.filter((r) => r.id !== req.id)
    members.value = await api.clubs.manageMembers(clubId.value)
    flash('탈퇴를 승인했습니다.')
  } catch (e) {
    flash(e.message, true)
  }
}

// --- 동아리 정보 -----------------------------------------------------

async function saveClubInfo() {
  try {
    const saved = await api.clubs.update(clubId.value, { ...clubEdit })
    club.value = { ...club.value, ...saved }
    savedClub.value = snap(clubEdit)
    popup('동아리 정보를 저장했습니다',
      `모집 ${clubEdit.recruit_status}` +
      (clubEdit.current_gen ? ` · 현재 ${clubEdit.current_gen}기` : ''))
  } catch (e) {
    popup('동아리 정보를 저장하지 못했습니다', e.message, false)
  }
}
</script>

<template>
  <section class="container page">
    <p class="eyebrow">동아리 관리</p>

    <div v-if="loading" class="sub">불러오는 중…</div>

    <div v-else-if="forbidden" class="warn">동아리장만 접근할 수 있습니다.</div>

    <template v-else-if="club">
      <h1 class="page-title">{{ club.name }} 관리</h1>
      <p class="sub">{{ club.category }} · {{ club.recruit_status }}</p>

      <p v-if="message" :class="messageIsError ? 'warn' : 'privacy'" class="flash">{{ message }}</p>

      <!-- 가입 신청자 -->
      <section class="card block">
        <h2 class="section-title">가입 신청자</h2>
        <p class="privacy">🔒 이름·학과·학년만 표시됩니다.</p>
        <p v-if="joinRequests.length === 0" class="sub">대기중인 신청이 없습니다.</p>
        <ul v-else class="list">
          <li v-for="r in joinRequests" :key="r.id" class="row">
            <div>
              <p class="card-title">{{ r.name }} <span class="sub">· {{ r.dept }}<template v-if="r.grade"> · {{ gradeLabel(r.grade) }}</template></span></p>
              <dl v-if="Object.keys(r.answers ?? {}).length" class="answers">
                <template v-for="(v, k) in r.answers" :key="k">
                  <dt>{{ questionOf[k] ?? k }}</dt>
                  <dd>{{ v || '—' }}</dd>
                </template>
              </dl>
            </div>
            <div class="actions">
              <button class="btn ghost" @click="openReject(r)">거절</button>
              <button class="btn" @click="approveRequest(r)">승인</button>
            </div>
          </li>
        </ul>
      </section>

      <!-- 가입폼 편집 -->
      <section class="card block">
        <h2 class="section-title">가입폼</h2>
        <label class="checkline">
          <input type="checkbox" v-model="formDraft.required" /> 가입폼 작성을 필수로 한다
        </label>
        <ul class="list">
          <li v-for="(f, i) in formDraft.fields" :key="i" class="field-card">
            <div class="field-head">
              <span class="qno">질문 {{ i + 1 }}</span>
              <button class="btn ghost icon" @click="removeField(i)" aria-label="질문 삭제">✕</button>
            </div>
            <div class="field-grid">
              <div class="fld">
                <label :for="`f-label-${i}`">질문 문구</label>
                <input :id="`f-label-${i}`" v-model="f.label"
                       placeholder="예: 지원 동기가 무엇인가요?" />
                <p class="hint">신청자에게 이대로 보입니다.</p>
              </div>
              <div class="fld">
                <label :for="`f-type-${i}`">답변 형식</label>
                <select :id="`f-type-${i}`" v-model="f.type">
                  <option value="text">한 줄</option>
                  <option value="textarea">여러 줄</option>
                </select>
              </div>
              <div class="fld">
                <label>필수 여부</label>
                <label class="checkline small">
                  <input type="checkbox" v-model="f.required" /> 반드시 답해야 함
                </label>
              </div>
            </div>
          </li>
        </ul>
        <div class="actions">
          <button class="btn ghost" @click="addField">질문 추가</button>
          <button class="btn" :disabled="!formDirty" @click="saveForm">
            {{ formDirty ? '가입폼 저장' : '변경사항 없음' }}
          </button>
        </div>
      </section>

      <!-- 부원 관리 -->
      <section class="card block">
        <h2 class="section-title">부원 관리</h2>
        <ul class="list">
          <li v-for="m in members" :key="m.user.id" class="member-card">
            <div class="who">
              <p class="card-title">
                {{ m.user.name }}
                <span v-if="m.role === '동아리장'" class="chip lead">동아리장</span>
              </p>
              <p class="sub">
                {{ m.user.dept }} · 학적 {{ m.academic_status }}
                <span class="lock" title="학적은 본인 또는 관리자만 바꿉니다">🔒</span>
              </p>
            </div>

            <div class="ctl">
              <label :for="`gen-${m.user.id}`">기수</label>
              <div class="gen-set">
                <input :id="`gen-${m.user.id}`" class="gen-input" type="number" min="1"
                       v-model="m.gen" @change="updateGen(m)" placeholder="—" />
                <span class="unit">기</span>
              </div>
            </div>

            <div class="ctl">
              <label :for="`ms-${m.user.id}`">동아리 상태</label>
              <select :id="`ms-${m.user.id}`" v-model="m.membership"
                      :disabled="m.role === '동아리장'"
                      @change="updateMembership(m)">
                <option value="활동중">활동중</option>
                <option value="OB">OB</option>
              </select>
            </div>

            <div class="actions">
              <button v-if="m.role !== '동아리장' && m.membership === '활동중'"
                      class="btn ghost" @click="openTransfer(m)">위임</button>
              <button v-if="m.role !== '동아리장'"
                      class="btn ghost danger" @click="openRemove(m)">내보내기</button>
            </div>
          </li>
        </ul>
      </section>

      <!-- 탈퇴 요청 -->
      <section class="card block">
        <h2 class="section-title">탈퇴 요청</h2>
        <p v-if="leaveRequests.length === 0" class="sub">대기중인 탈퇴 요청이 없습니다.</p>
        <ul v-else class="list">
          <li v-for="r in leaveRequests" :key="r.id" class="row">
            <p class="card-title">{{ r.user.name }} <span class="sub">· {{ r.user.dept }} · {{ r.status }}</span></p>
            <button v-if="r.status === '심사중'" class="btn" @click="approveLeave(r)">승인</button>
          </li>
        </ul>
      </section>

      <!-- 동아리 정보 -->
      <section class="card block">
        <h2 class="section-title">동아리 정보</h2>
        <div class="row-2">
          <div>
            <label>모집 상태</label>
            <select v-model="clubEdit.recruit_status">
              <option value="모집중">모집중</option>
              <option value="모집마감">모집마감</option>
              <option value="상시모집">상시모집</option>
            </select>
          </div>
          <div>
            <label>현재 기수</label>
            <input type="number" v-model.number="clubEdit.current_gen" />
          </div>
        </div>
        <div class="row-3">
          <div><label>정기모임 요일</label><input v-model="clubEdit.meet_day" /></div>
          <div><label>시간</label><input v-model="clubEdit.meet_time" /></div>
          <div><label>장소</label><input v-model="clubEdit.meet_place" /></div>
        </div>
        <div>
          <label>소개</label>
          <textarea v-model="clubEdit.purpose" rows="4" />
        </div>
        <button class="btn" :disabled="!clubDirty" @click="saveClubInfo">
          {{ clubDirty ? '저장' : '변경사항 없음' }}
        </button>
      </section>
    </template>

    <dialog ref="rejectDialog" class="narrow" @click.self="rejectDialog.close()">
      <div class="sheet">
        <header class="sheet-head">
          <h2 class="section-title">가입 거절</h2>
          <button class="btn ghost icon" @click="rejectDialog.close()" aria-label="닫기">✕</button>
        </header>
        <div class="sheet-body">
          <label>사유 (선택)</label>
          <textarea v-model="rejectReason" rows="3" />
        </div>
        <div class="sheet-actions">
          <button class="btn ghost" @click="rejectDialog.close()">취소</button>
          <button class="btn" @click="confirmReject">거절하기</button>
        </div>
      </div>
    </dialog>

    <dialog ref="transferDialog" class="narrow" @click.self="transferDialog.close()">
      <div class="sheet">
        <header class="sheet-head">
          <h2 class="section-title">동아리장 위임</h2>
          <button class="btn ghost icon" @click="transferDialog.close()" aria-label="닫기">✕</button>
        </header>
        <div class="sheet-body">
          <p class="warn" v-if="transferTarget">
            {{ transferTarget.user.name }}님에게 동아리장을 위임하면 본인은 부원이 됩니다.
          </p>
        </div>
        <div class="sheet-actions">
          <button class="btn ghost" @click="transferDialog.close()">취소</button>
          <button class="btn" @click="confirmTransfer">위임하기</button>
        </div>
      </div>
    </dialog>

    <!-- 부원 내보내기 확인 -->
    <dialog ref="removeDialog" class="narrow" @click.self="removeDialog.close()">
      <div class="sheet">
        <header class="sheet-head">
          <h2 class="section-title">부원 내보내기</h2>
          <button class="btn ghost icon" @click="removeDialog.close()" aria-label="닫기">✕</button>
        </header>
        <div class="sheet-body">
          <p class="warn" v-if="removeTarget">
            {{ removeTarget.user.name }}님을 동아리에서 내보냅니다. 기수·소속 기록이 사라지며
            되돌릴 수 없습니다. 본인이 다시 가입 신청할 수는 있습니다.
          </p>
        </div>
        <div class="sheet-actions">
          <button class="btn ghost" @click="removeDialog.close()">취소</button>
          <button class="btn danger-fill" @click="confirmRemove">내보내기</button>
        </div>
      </div>
    </dialog>

    <!-- 저장 결과 -->
    <dialog ref="resultDlg" class="narrow" @click.self="resultDlg.close()">
      <div class="sheet">
        <header class="sheet-head">
          <h2 class="section-title">{{ result.ok ? '✓' : '✕' }} {{ result.title }}</h2>
          <button class="btn ghost icon" @click="resultDlg.close()" aria-label="닫기">✕</button>
        </header>
        <div class="sheet-body">
          <p :class="result.ok ? 'privacy' : 'warn'">{{ result.detail }}</p>
        </div>
        <div class="sheet-actions">
          <button class="btn" @click="resultDlg.close()">확인</button>
        </div>
      </div>
    </dialog>
  </section>
</template>

<style scoped>
/* 저장 이름이 규칙에 어긋나면 안내를 붉게 — 저장 버튼을 누르기 전에 알아채게 */
.hint.bad { color: var(--dangerInk); }

.page { padding: 56px 0 140px; }
.flash { margin: 16px 0; }
.block { padding: 22px; margin-top: 18px; display: flex; flex-direction: column; gap: 14px; }
.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--line); }
.row:last-child { border-bottom: none; }
.actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.answers { margin: 6px 0 0; display: grid; grid-template-columns: auto 1fr; gap: 3px 10px; }
.answers dt { font-size: 12px; font-weight: 700; color: var(--dim); white-space: nowrap; }
.answers dd { margin: 0; font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; }
.checkline { display: flex; align-items: center; gap: 8px; font-weight: 400; margin: 0; }
.checkline.small { font-size: 12.5px; }
.checkline input { width: auto; }
/* 가입폼 — 어떤 값을 넣는 칸인지 라벨로 드러낸다 */
.field-card { border: var(--border); border-radius: 14px; padding: 14px 16px; background: var(--bg); }
.field-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.qno { font-size: 11px; font-weight: 700; letter-spacing: .12em; color: var(--dim); }
.field-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 12px 16px; }
.field-grid .fld:nth-child(3) { grid-column: 1; }
.fld label { display: block; font-size: 12.5px; font-weight: 700; margin-bottom: 5px; }
.fld .hint { margin-top: 4px; }

/* 부원 — 기수를 '바꾸는 칸'으로 읽히게 라벨과 단위를 붙인다 */
.member-card {
  display: grid; grid-template-columns: 1fr auto auto auto; gap: 16px;
  align-items: end; padding: 14px 0; border-bottom: 1px solid var(--line);
}
.member-card:last-child { border-bottom: none; }
.member-card .who { min-width: 0; }
.member-card .ctl label { display: block; font-size: 11.5px; font-weight: 700; color: var(--dim); margin-bottom: 5px; }
.gen-set { display: flex; align-items: center; gap: 6px; }
.gen-input { width: 68px; text-align: center; }
.gen-set .unit { font-size: 13px; color: var(--dim); }
.member-card select { width: auto; }
.chip.lead { background: var(--accent); color: var(--onAccent); margin-left: 6px; }
.lock { font-size: 11px; opacity: .55; }

/* 취소·삭제 같은 부정 동작은 붉은 계열로 (디자인 기획 §4) */
.btn.danger { border-color: var(--dangerLine); color: var(--dangerInk); }
.btn.danger:hover { background: var(--dangerBg); }
.btn.danger-fill { background: var(--dangerInk); color: var(--card); border-color: var(--dangerInk); }

.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.sheet-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px; border-bottom: var(--border);
}
.sheet-body { padding: 18px 20px; display: flex; flex-direction: column; gap: 10px; }
.sheet-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 20px; border-top: var(--border); }
</style>
