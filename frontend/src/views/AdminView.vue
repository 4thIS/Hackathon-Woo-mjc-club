<script setup>
/* T4 · 담당 th. 명세: docs/api.md §5 — 개설 신청 승인/거절(사유 필수) · 보관 전환 · 동아리장 강제 교체
 * 유저 관리 탭은 T4-C 복구분 (wj) — AdminUserPanel.vue
 * 게시글 전체 관리는 컷라인 유지 (api.md §10)
 */
import { onMounted, ref } from 'vue'
import api from '../api'
import AdminClubPanel from '../components/AdminClubPanel.vue'
import AdminUserPanel from '../components/AdminUserPanel.vue'

const tab = ref('applications')   // applications | clubs | users
const TITLES = { applications: '동아리 개설 신청', clubs: '동아리 관리', users: '유저 관리' }

const statusFilter = ref('심사중')
const applications = ref([])
const loading = ref(true)
const message = ref('')

function flash(text) {
  message.value = text
  setTimeout(() => { if (message.value === text) message.value = '' }, 3500)
}

async function load() {
  loading.value = true
  try {
    applications.value = await api.admin.applications(statusFilter.value || undefined)
  } catch (e) {
    flash(e.message)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function approve(app) {
  try {
    await api.admin.approve(app.id)
    applications.value = applications.value.filter((a) => a.id !== app.id)
    flash(`${app.name} 승인 완료 — 동아리가 개설됐습니다.`)
  } catch (e) {
    flash(e.message)
  }
}

const rejectDialog = ref(null)
const rejectTarget = ref(null)
const rejectReason = ref('')

function openReject(app) {
  rejectTarget.value = app
  rejectReason.value = ''
  rejectDialog.value.showModal()
}

async function confirmReject() {
  if (!rejectReason.value.trim()) return
  try {
    await api.admin.reject(rejectTarget.value.id, rejectReason.value.trim())
    applications.value = applications.value.filter((a) => a.id !== rejectTarget.value.id)
    rejectDialog.value.close()
    flash('거절 처리했습니다.')
  } catch (e) {
    flash(e.message)
  }
}
</script>

<template>
  <section class="container page">
    <p class="eyebrow">관리자</p>
    <h1 class="page-title">{{ TITLES[tab] }}</h1>

    <div class="tabs" role="tablist">
      <button class="tab" :class="{ on: tab === 'applications' }" role="tab"
              :aria-selected="tab === 'applications'" @click="tab = 'applications'">
        개설 신청
      </button>
      <button class="tab" :class="{ on: tab === 'clubs' }" role="tab"
              :aria-selected="tab === 'clubs'" @click="tab = 'clubs'">
        동아리
      </button>
      <button class="tab" :class="{ on: tab === 'users' }" role="tab"
              :aria-selected="tab === 'users'" @click="tab = 'users'">
        유저
      </button>
    </div>

    <AdminClubPanel v-if="tab === 'clubs'" />
    <AdminUserPanel v-else-if="tab === 'users'" />

    <template v-else>
    <div class="filter">
      <select v-model="statusFilter" @change="load">
        <option value="심사중">심사중</option>
        <option value="승인">승인</option>
        <option value="거절">거절</option>
        <option value="">전체</option>
      </select>
    </div>

    <p v-if="message" class="privacy flash">{{ message }}</p>
    <p v-if="loading" class="sub">불러오는 중…</p>
    <p v-else-if="applications.length === 0" class="sub">해당 상태의 신청이 없습니다.</p>

    <ul v-else class="list">
      <li v-for="a in applications" :key="a.id" class="card row">
        <div>
          <p class="card-title">{{ a.name }} <span class="chip">{{ a.category }}</span></p>
          <p class="sub">{{ a.founded_year }}년 · 지도교수 {{ a.advisor || '-' }} · 신청자 {{ a.applicant.name }}({{ a.applicant.dept }})</p>
          <p class="sub">{{ a.purpose }}</p>
        </div>
        <div v-if="a.status === '심사중'" class="actions">
          <button class="btn ghost" @click="openReject(a)">거절</button>
          <button class="btn" @click="approve(a)">승인</button>
        </div>
        <p v-else class="chip">{{ a.status }}</p>
      </li>
    </ul>

    <dialog ref="rejectDialog" class="narrow" @click.self="rejectDialog.close()">
      <div class="sheet">
        <header class="sheet-head">
          <h2 class="section-title">개설 신청 거절</h2>
          <button class="btn ghost icon" @click="rejectDialog.close()" aria-label="닫기">✕</button>
        </header>
        <div class="sheet-body">
          <label>사유 <span class="req">*</span></label>
          <textarea v-model="rejectReason" rows="3" placeholder="유사 동아리가 이미 있습니다" />
          <p class="hint">사유는 신청자에게 메일로 전달됩니다.</p>
        </div>
        <div class="sheet-actions">
          <button class="btn ghost" @click="rejectDialog.close()">취소</button>
          <button class="btn" :disabled="!rejectReason.trim()" @click="confirmReject">거절하기</button>
        </div>
      </div>
    </dialog>
    </template>
  </section>
</template>

<style scoped>
.tabs { display: flex; gap: 6px; margin: 16px 0 20px; border-bottom: 1px solid var(--line); }
.tab {
  background: none; border: none; border-bottom: 2px solid transparent;
  padding: 10px 14px; margin-bottom: -1px;
  font: inherit; font-size: 14px; font-weight: 700; color: var(--dim); cursor: pointer;
}
.tab:hover { color: var(--ink); }
.tab.on { color: var(--accent); border-bottom-color: var(--accent); }

.page { padding: 56px 0 140px; }
.filter { margin: 16px 0 8px; max-width: 160px; }
.flash { margin-bottom: 12px; }
.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 12px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px; }
.actions { display: flex; gap: 8px; flex-shrink: 0; }
.sheet-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px; border-bottom: var(--border);
}
.sheet-body { padding: 18px 20px; display: flex; flex-direction: column; gap: 6px; }
.sheet-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 20px; border-top: var(--border); }
</style>
