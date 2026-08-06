<script setup>
/* T3 · T4 담당 th. 명세: docs/api.md §4
 * 가입폼 편집 · 신청자 승인/거절 · 부원 관리(기수/위임) · 탈퇴 요청 승인 · 동아리 정보 수정
 */
import { computed, onMounted, reactive, ref } from 'vue'
import api, { ApiError } from '../api'

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

function flash(text, isError = false) {
  message.value = text
  messageIsError.value = isError
  setTimeout(() => { if (message.value === text) message.value = '' }, 3500)
}

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
    formDraft.fields = form.fields
    joinRequests.value = reqs
    members.value = mem
    leaveRequests.value = leaves
    clubEdit.purpose = c.purpose ?? ''
    clubEdit.meet_day = c.meet_day ?? ''
    clubEdit.meet_time = c.meet_time ?? ''
    clubEdit.meet_place = c.meet_place ?? ''
    clubEdit.recruit_status = c.recruit_status
    clubEdit.current_gen = c.current_gen
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

function addField() {
  formDraft.fields.push({ key: `q${formDraft.fields.length + 1}`, label: '', type: 'text', required: false })
}
function removeField(i) {
  formDraft.fields.splice(i, 1)
}
async function saveForm() {
  try {
    const saved = await api.joinForm.put(clubId.value, formDraft)
    formDraft.required = saved.required
    formDraft.fields = saved.fields
    flash('가입폼을 저장했습니다.')
  } catch (e) {
    flash(e.message, true)
  }
}

// --- 부원 관리 -------------------------------------------------------

async function updateGen(m) {
  try {
    await api.clubs.updateMember(clubId.value, m.user.id, { gen: m.gen === '' ? null : Number(m.gen) })
    flash(`${m.user.name}님 기수를 수정했습니다.`)
  } catch (e) {
    flash(e.message, true)
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
    flash('동아리 정보를 저장했습니다.')
  } catch (e) {
    flash(e.message, true)
  }
}
</script>

<template>
  <section class="container page">
    <p class="eyebrow">T3 · T4 · 동아리 관리</p>

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
              <p class="card-title">{{ r.name }} <span class="sub">· {{ r.dept }}<template v-if="r.grade"> · {{ r.grade }}학년</template></span></p>
              <p v-if="Object.keys(r.answers ?? {}).length" class="sub answers">
                <span v-for="(v, k) in r.answers" :key="k">{{ k }}: {{ v }}</span>
              </p>
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
          <li v-for="(f, i) in formDraft.fields" :key="i" class="field-row">
            <input v-model="f.key" placeholder="key" class="key" />
            <input v-model="f.label" placeholder="질문" class="label-input" />
            <select v-model="f.type">
              <option value="text">한 줄</option>
              <option value="textarea">여러 줄</option>
            </select>
            <label class="checkline small"><input type="checkbox" v-model="f.required" /> 필수</label>
            <button class="btn ghost icon" @click="removeField(i)" aria-label="삭제">✕</button>
          </li>
        </ul>
        <div class="actions">
          <button class="btn ghost" @click="addField">질문 추가</button>
          <button class="btn" @click="saveForm">가입폼 저장</button>
        </div>
      </section>

      <!-- 부원 관리 -->
      <section class="card block">
        <h2 class="section-title">부원 관리</h2>
        <ul class="list">
          <li v-for="m in members" :key="m.user.id" class="row member-row">
            <div>
              <p class="card-title">{{ m.user.name }} <span class="sub">· {{ m.user.dept }}</span></p>
              <p class="sub">{{ m.role }} · {{ m.membership }}</p>
            </div>
            <div class="actions">
              <input
                class="gen-input"
                type="number"
                v-model="m.gen"
                @change="updateGen(m)"
                placeholder="기수" />
              <button
                v-if="m.role !== '동아리장' && m.membership === '활동중'"
                class="btn ghost"
                @click="openTransfer(m)">
                위임
              </button>
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
        <button class="btn" @click="saveClubInfo">저장</button>
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
  </section>
</template>

<style scoped>
.page { padding: 56px 0 140px; }
.flash { margin: 16px 0; }
.block { padding: 22px; margin-top: 18px; display: flex; flex-direction: column; gap: 14px; }
.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--line); }
.row:last-child { border-bottom: none; }
.actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.answers span { display: block; }
.checkline { display: flex; align-items: center; gap: 8px; font-weight: 400; margin: 0; }
.checkline.small { font-size: 12.5px; }
.checkline input { width: auto; }
.field-row { display: grid; grid-template-columns: 100px 1fr 110px auto auto; gap: 8px; align-items: center; }
.gen-input { width: 72px; }
.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.sheet-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px; border-bottom: var(--border);
}
.sheet-body { padding: 18px 20px; display: flex; flex-direction: column; gap: 10px; }
.sheet-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 20px; border-top: var(--border); }
</style>
