<script setup>
/* 관리자 — 동아리 관리. 명세: docs/api.md §5 · 기획서 §5.5(강제 교체) §5.6(보관)
 *
 * 권한은 원래 있었다 — deps.club_leader 가 관리자를 통과시킨다.
 * 없던 건 진입로다. 공개 목록이 활동중만 주기 때문에 보관된 동아리에 도달할 수 없었다.
 */
import { onMounted, reactive, ref } from 'vue'
import api from '../api'
import { CATEGORY_NAMES as CATEGORIES } from './ClubCategory'

const clubs = ref([])
const total = ref(0)
const loading = ref(true)
const filters = reactive({ q: '', status: '', category: '' })
const message = ref('')

const dlg = ref(null)
const target = ref(null)      // 교체 대상 동아리
const members = ref([])
const pickedLeader = ref('')
const busy = ref(false)
const error = ref('')

/* 동아리 정보 수정 모달 — 목록을 벗어나지 않고 그 자리에서 고친다 */
const editDlg = ref(null)
const editing = ref(null)
const form = reactive({
  purpose: '', meet_day: '', meet_time: '', meet_place: '',
  recruit_status: '', current_gen: null,
})
const saving = ref(false)
const editError = ref('')

const RECRUIT = ['모집중', '모집마감', '상시모집']

async function openEdit(club) {
  editing.value = club
  editError.value = ''
  Object.assign(form, {
    purpose: '', meet_day: '', meet_time: '', meet_place: '',
    recruit_status: club.recruit_status, current_gen: club.current_gen,
  })
  editDlg.value?.showModal()
  try {
    // 목록에는 없는 소개·정기모임을 상세에서 채워 온다
    const d = await api.clubs.detail(club.id)
    Object.assign(form, {
      purpose: d.purpose ?? '',
      meet_day: d.meet_day ?? '',
      meet_time: d.meet_time ?? '',
      meet_place: d.meet_place ?? '',
      recruit_status: d.recruit_status,
      current_gen: d.current_gen,
    })
  } catch (e) {
    editError.value = e.message
  }
}

async function saveEdit() {
  editError.value = ''
  saving.value = true
  try {
    // 관리자는 동아리장 전용 API 도 통과한다 (deps.club_leader)
    await api.clubs.update(editing.value.id, { ...form })
    editing.value.recruit_status = form.recruit_status
    editing.value.current_gen = form.current_gen
    editDlg.value?.close()
    flash(`${editing.value.name} 정보를 수정했습니다.`)
  } catch (e) {
    editError.value = e.message
  } finally {
    saving.value = false
  }
}

function flash(text) {
  message.value = text
  setTimeout(() => { if (message.value === text) message.value = '' }, 3500)
}

async function load() {
  loading.value = true
  try {
    const r = await api.admin.clubs({
      q: filters.q || undefined,
      status: filters.status || undefined,
      category: filters.category || undefined,
    })
    clubs.value = r.items
    total.value = r.total
  } catch (e) {
    flash(e.message)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function toggleArchive(club) {
  const next = club.status === '보관' ? '활동중' : '보관'
  try {
    await api.admin.updateClub(club.id, { status: next })
    club.status = next
    flash(next === '보관'
      ? `${club.name} 을 보관했습니다. 활동 기록은 그대로 남습니다.`
      : `${club.name} 을 다시 활동중으로 되돌렸습니다.`)
  } catch (e) {
    flash(e.message)
  }
}

async function openTransfer(club) {
  target.value = club
  pickedLeader.value = ''
  error.value = ''
  members.value = []
  dlg.value?.showModal()
  try {
    // 관리자는 동아리장 전용 API 도 통과한다 (deps.club_leader)
    members.value = await api.clubs.manageMembers(club.id)
  } catch (e) {
    error.value = e.message
  }
}

async function transfer() {
  if (!pickedLeader.value) return
  error.value = ''
  busy.value = true
  try {
    await api.admin.updateClub(target.value.id, { leader_id: pickedLeader.value })
    // 부원 응답은 { user: {...}, role, membership, gen } 형태다 (api.md §4)
    const picked = members.value.find((m) => m.user.id === pickedLeader.value)
    target.value.leader = picked ? { ...picked.user } : null
    dlg.value?.close()
    flash(`${target.value.name} 의 동아리장을 ${picked?.user.name} 님으로 바꿨습니다.`)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div>
    <div class="bar">
      <input v-model="filters.q" placeholder="동아리 이름 · 분야" @keyup.enter="load">
      <select v-model="filters.category" @change="load">
        <option value="">분야 전체</option>
        <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="filters.status" @change="load">
        <option value="">운영 전체</option>
        <option value="활동중">활동중</option>
        <option value="보관">보관</option>
      </select>
      <button class="btn ghost" @click="load">검색</button>
      <span class="sub count">{{ total }}개</span>
    </div>

    <p v-if="message" class="privacy flash">{{ message }}</p>
    <p v-if="loading" class="sub">불러오는 중…</p>
    <p v-else-if="!clubs.length" class="sub">조건에 맞는 동아리가 없습니다.</p>

    <ul v-else class="list">
      <li v-for="c in clubs" :key="c.id" :class="{ archived: c.status === '보관' }">
        <div class="who">
          <RouterLink class="nm" :to="`/clubs/${c.id}`">{{ c.name }}</RouterLink>
          <span class="chip">{{ c.category }}</span>
          <span class="chip" :class="{ rec: c.recruit_status === '모집중' }">{{ c.recruit_status }}</span>
          <span v-if="c.status === '보관'" class="chip arch">보관</span>
        </div>

        <div class="meta sub">
          부원 {{ c.member_count }} · 활동 {{ c.post_count }}
          <template v-if="c.current_gen"> · {{ c.current_gen }}기</template>
          ·
          <template v-if="c.leader">동아리장 {{ c.leader.name }}</template>
          <b v-else class="noleader">동아리장 없음</b>
        </div>

        <div class="acts">
          <button class="btn ghost sm" @click="openEdit(c)">관리</button>
          <button class="btn ghost sm" @click="openTransfer(c)">동아리장 교체</button>
          <button class="btn ghost sm" :class="{ danger: c.status !== '보관' }"
                  @click="toggleArchive(c)">
            {{ c.status === '보관' ? '복구' : '보관' }}
          </button>
        </div>
      </li>
    </ul>

    <!-- 동아리 정보 수정 -->
    <dialog ref="editDlg" @click.self="editDlg.close()">
      <div class="sheet-hd">
        <h2>{{ editing?.name }}</h2>
        <p>이름·분야·창립년도·지도교수는 개설 때 확정됩니다 (기획서 §5.1).</p>
        <button class="x" aria-label="닫기" @click="editDlg.close()">✕</button>
      </div>

      <form class="sheet-bd" @submit.prevent="saveEdit">
        <div class="fld">
          <label for="ac-purpose">소개</label>
          <textarea id="ac-purpose" v-model="form.purpose" rows="4"
                    placeholder="어떤 활동을 하는 동아리인지"></textarea>
        </div>

        <div class="two">
          <div class="fld">
            <label for="ac-recruit">모집 상태</label>
            <select id="ac-recruit" v-model="form.recruit_status">
              <option v-for="r in RECRUIT" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
          <div class="fld">
            <label for="ac-gen">현재 기수</label>
            <input id="ac-gen" v-model.number="form.current_gen" type="number" min="1">
            <p class="hint">가입 승인 시 이 기수가 부여됩니다.</p>
          </div>
        </div>

        <p class="k">정기 모임</p>
        <div class="three">
          <div class="fld">
            <label for="ac-day">요일</label>
            <input id="ac-day" v-model="form.meet_day" placeholder="수요일">
          </div>
          <div class="fld">
            <label for="ac-time">시간</label>
            <input id="ac-time" v-model="form.meet_time" placeholder="18:00">
          </div>
          <div class="fld">
            <label for="ac-place">장소</label>
            <input id="ac-place" v-model="form.meet_place" placeholder="학생회관 302">
          </div>
        </div>

        <p v-if="editError" class="warn err">{{ editError }}</p>
        <button class="hidden-submit" type="submit" tabindex="-1" aria-hidden="true"></button>
      </form>

      <div class="sheet-ft">
        <RouterLink v-if="editing" class="btn ghost" :to="`/clubs/${editing.id}/manage`">
          전체 관리 화면
        </RouterLink>
        <button class="btn" type="button" :disabled="saving" @click="saveEdit">
          {{ saving ? '저장 중…' : '저장' }}
        </button>
      </div>
    </dialog>

    <!-- 동아리장 강제 교체 (기획서 §5.5) -->
    <dialog ref="dlg" class="narrow" @click.self="dlg.close()">
      <div class="sheet-hd">
        <h2>동아리장 교체</h2>
        <p>{{ target?.name }} — 활동중인 부원만 지정할 수 있습니다.</p>
        <button class="x" aria-label="닫기" @click="dlg.close()">✕</button>
      </div>

      <div class="sheet-bd">
        <p v-if="!members.length && !error" class="sub">부원을 불러오는 중…</p>
        <p v-else-if="!members.filter((m) => m.membership === '활동중').length" class="warn">
          활동중인 부원이 없습니다. 먼저 부원을 받아야 동아리장을 지정할 수 있습니다.
        </p>

        <ul v-else class="picks">
          <li v-for="m in members.filter((x) => x.membership === '활동중')" :key="m.user.id">
            <label class="pick">
              <input v-model="pickedLeader" type="radio" :value="m.user.id">
              <span class="pnm">{{ m.user.name }}</span>
              <span class="sub">
                {{ m.user.dept }}<template v-if="m.gen"> · {{ m.gen }}기</template>
              </span>
              <span v-if="m.role === '동아리장'" class="chip">현재 동아리장</span>
            </label>
          </li>
        </ul>

        <p v-if="error" class="warn err">{{ error }}</p>
      </div>

      <div class="sheet-ft">
        <button class="btn ghost" type="button" @click="dlg.close()">취소</button>
        <button class="btn" type="button" :disabled="!pickedLeader || busy" @click="transfer">
          {{ busy ? '바꾸는 중…' : '교체하기' }}
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
.list li.archived { opacity: .62; }
.who { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 280px; }
.nm { font-weight: 700; font-size: 15px; text-decoration: none; color: var(--ink); }
.nm:hover { color: var(--accent); }
.chip.rec { background: var(--accent); color: var(--onAccent); }
.chip.arch { background: transparent; border: 1.5px solid var(--line); color: var(--dim); }
.meta { flex: 1; min-width: 180px; }
.noleader { color: var(--warnInk); font-weight: 700; }

.acts { display: flex; gap: 6px; flex-wrap: wrap; }
.btn.sm { height: 32px; padding: 0 12px; font-size: 12.5px; text-decoration: none; }
.btn.sm.danger { border-color: var(--warnLine); color: var(--warnInk); }

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
.three { display: grid; grid-template-columns: 1fr 1fr 1.4fr; gap: 0 12px; }
.k { font-size: 11px; font-weight: 700; letter-spacing: .13em; color: var(--dim); margin: 4px 0 8px; }
.sheet-ft .btn.ghost { text-decoration: none; }
.hidden-submit { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }

.picks { list-style: none; margin: 0; padding: 0; }
.pick {
  display: flex; align-items: center; gap: 9px; flex-wrap: wrap;
  padding: 10px 0; border-bottom: 1px solid var(--line);
  font-size: 14px; font-weight: 400; margin: 0; cursor: pointer;
}
.pick input { width: auto; }
.pnm { font-weight: 700; }
.err { margin: 14px 0 0; }

@media (max-width: 560px) {
  .two, .three { grid-template-columns: 1fr; }
}
</style>
