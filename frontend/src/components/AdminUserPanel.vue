<script setup>
/* 관리자 — 유저 관리. 명세: docs/api.md §5 · 기획서 §3.2, §4.3
 *
 * 기획서 §4.3 이 잠긴 필드에 대해 "변경이 필요하면 관리자 문의" 라고 안내한다.
 * 그 문의를 받아주는 화면이 여기다. 학번(PK)만 못 바꾼다.
 */
import { onMounted, reactive, ref } from 'vue'
import api from '../api'
import { useAuth } from '../stores/auth'

const auth = useAuth()

const users = ref([])
const total = ref(0)
const loading = ref(true)
const filters = reactive({ q: '', status: '', admin: '' })
const message = ref('')

const dlg = ref(null)
const editing = ref(null)      // 원본
const form = reactive({})      // 수정본
const saving = ref(false)
const error = ref('')

function flash(text) {
  message.value = text
  setTimeout(() => { if (message.value === text) message.value = '' }, 3500)
}

async function load() {
  loading.value = true
  try {
    const r = await api.admin.users({
      q: filters.q || undefined,
      status: filters.status || undefined,
      admin: filters.admin || undefined,
    })
    users.value = r.items
    total.value = r.total
  } catch (e) {
    flash(e.message)
  } finally {
    loading.value = false
  }
}
onMounted(load)

function edit(u) {
  editing.value = u
  error.value = ''
  Object.assign(form, {
    name: u.name, dept: u.dept, birth: u.birth, gender: u.gender,
    email: u.email, academic_status: u.academic_status,
    email_verified: u.email_verified, is_admin: u.is_admin,
  })
  dlg.value?.showModal()
}

async function save() {
  error.value = ''
  saving.value = true
  try {
    const updated = await api.admin.updateUser(editing.value.id, { ...form })
    const i = users.value.findIndex((u) => u.id === updated.id)
    if (i >= 0) users.value[i] = updated
    // 자기 자신을 고쳤으면 헤더의 로그인 정보도 맞춰준다
    if (updated.id === auth.user?.id) auth.user = { ...auth.user, ...updated }
    dlg.value?.close()
    flash(`${updated.name} 정보를 수정했습니다.`)
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

const leaderOf = (u) => u.clubs.filter((c) => c.role === '동아리장')
</script>

<template>
  <div>
    <div class="bar">
      <input v-model="filters.q" placeholder="이름 · 학번 · 학과 · 이메일" @keyup.enter="load">
      <select v-model="filters.status" @change="load">
        <option value="">학적 전체</option>
        <option value="재학">재학</option>
        <option value="휴학">휴학</option>
        <option value="졸업">졸업</option>
      </select>
      <select v-model="filters.admin" @change="load">
        <option value="">권한 전체</option>
        <option value="true">관리자만</option>
        <option value="false">일반만</option>
      </select>
      <button class="btn ghost" @click="load">검색</button>
      <span class="sub count">{{ total }}명</span>
    </div>

    <p v-if="message" class="privacy flash">{{ message }}</p>
    <p v-if="loading" class="sub">불러오는 중…</p>
    <p v-else-if="!users.length" class="sub">조건에 맞는 유저가 없습니다.</p>

    <ul v-else class="list">
      <li v-for="u in users" :key="u.id">
        <div class="who">
          <span class="nm">{{ u.name }}</span>
          <span v-if="u.is_admin" class="chip adm">관리자</span>
          <span v-if="!u.email_verified" class="chip warnchip">미인증</span>
          <span class="sub">{{ u.id }} · {{ u.dept }} · {{ u.grade }}학년 · {{ u.academic_status }}</span>
        </div>

        <div class="clubs">
          <span v-if="!u.clubs.length" class="sub">소속 없음</span>
          <template v-else>
            <span v-for="c in u.clubs" :key="c.id" class="chip"
                  :class="{ lead: c.role === '동아리장', ob: c.membership === 'OB' }">
              {{ c.name }}<template v-if="c.role === '동아리장'"> · 장</template>
            </span>
          </template>
        </div>

        <button class="btn ghost sm" @click="edit(u)">수정</button>
      </li>
    </ul>

    <!-- 수정 모달 (디자인 기획 §6-2) -->
    <dialog ref="dlg" @click.self="dlg.close()">
      <div class="sheet-hd">
        <h2>{{ editing?.name }} 정보 수정</h2>
        <p>학번 {{ editing?.id }} — 학번은 계정 식별자라 바꿀 수 없습니다.</p>
        <button class="x" aria-label="닫기" @click="dlg.close()">✕</button>
      </div>

      <form class="sheet-bd" @submit.prevent="save">
        <div class="two">
          <div class="fld">
            <label for="au-name">이름</label>
            <input id="au-name" v-model="form.name">
          </div>
          <div class="fld">
            <label for="au-dept">학과</label>
            <input id="au-dept" v-model="form.dept">
          </div>
        </div>

        <div class="two">
          <div class="fld">
            <label for="au-birth">생년월일</label>
            <input id="au-birth" v-model="form.birth" type="date">
          </div>
          <div class="fld">
            <label for="au-gender">성별</label>
            <select id="au-gender" v-model="form.gender">
              <option value="남">남</option>
              <option value="여">여</option>
            </select>
          </div>
        </div>

        <div class="fld">
          <label for="au-email">이메일</label>
          <input id="au-email" v-model="form.email">
          <p class="hint">학교 도메인만 쓸 수 있고, 학번과 일치해야 합니다.</p>
        </div>

        <div class="fld">
          <label for="au-status">학적 상태</label>
          <select id="au-status" v-model="form.academic_status">
            <option value="재학">재학</option>
            <option value="휴학">휴학</option>
            <option value="졸업">졸업</option>
          </select>
          <p v-if="editing && leaderOf(editing).length" class="hint warntext">
            {{ leaderOf(editing).map((c) => c.name).join(' · ') }} 의 동아리장입니다.
            먼저 동아리장을 교체해야 졸업으로 바꿀 수 있습니다.
          </p>
        </div>

        <div class="toggles">
          <label class="tog"><input v-model="form.email_verified" type="checkbox"> 이메일 인증됨</label>
          <label class="tog"><input v-model="form.is_admin" type="checkbox"> 관리자 권한</label>
        </div>

        <p v-if="error" class="warn err">{{ error }}</p>
        <button class="hidden-submit" type="submit" tabindex="-1" aria-hidden="true"></button>
      </form>

      <div class="sheet-ft">
        <button class="btn ghost" type="button" @click="dlg.close()">취소</button>
        <button class="btn" type="button" :disabled="saving" @click="save">
          {{ saving ? '저장 중…' : '저장' }}
        </button>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
.bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }
.bar input { flex: 1; min-width: 200px; }
.bar select { width: auto; }
.count { margin-left: auto; }
.flash { margin-bottom: 14px; }

.list { list-style: none; margin: 0; padding: 0; }
.list li {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  padding: 14px 0; border-bottom: 1px solid var(--line);
}
.who { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 260px; }
.nm { font-weight: 700; font-size: 15px; }
.clubs { display: flex; gap: 6px; flex-wrap: wrap; flex: 1; }
.chip.adm { background: var(--accent); color: var(--onAccent); }
.chip.warnchip { background: var(--warnBg); color: var(--warnInk); }
.chip.lead { border: 1.5px solid var(--accent); }
.chip.ob { opacity: .6; }
.btn.sm { height: 32px; padding: 0 12px; font-size: 12.5px; }

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
.toggles { display: flex; gap: 18px; flex-wrap: wrap; margin: 4px 0 14px; }
.tog { display: flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 600; margin: 0; }
.tog input { width: auto; }
.warntext { color: var(--warnInk); }
.err { margin: 0 0 14px; }
.hidden-submit { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }

@media (max-width: 560px) { .two { grid-template-columns: 1fr; } }
</style>
