<script setup>
/* 동아리 상세 — 디자인 기획 §5.3 (mockups/club.html 이식)
 * api.md §3 GET /clubs/{id} · /posts · /members, §4 join-form · join-requests
 * 헤더는 전역 SiteHeader 가 담당하므로 목업 <header> 는 이식하지 않는다. */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../api'
import { useAuth } from '../stores/auth'
import ClubTimeline from '../components/ClubTimeline.vue'
import ClubMembersDialog from '../components/ClubMembersDialog.vue'
import ClubJoinDialog from '../components/ClubJoinDialog.vue'
import { catVars, catEmoji } from '../components/ClubCategory'

const props = defineProps({ id: { type: String, required: true } })

const router = useRouter()
const route = useRoute()
const auth = useAuth()

const club = ref(null)
const loading = ref(true)
const loadError = ref('')
const applied = ref(false)

const membersDlg = ref(null)
const joinDlg = ref(null)
const closedDlg = ref(null)

const RECRUITING = ['모집중', '상시모집']

const phVars = computed(() => catVars(club.value?.category))
const emoji = computed(() => catEmoji(club.value?.category))
const paragraphs = computed(() =>
  (club.value?.purpose ?? '').split(/\n+/).map((s) => s.trim()).filter(Boolean),
)
const recruitOpen = computed(() => RECRUITING.includes(club.value?.recruit_status))
const memberCount = computed(() => club.value?.counts?.total ?? 0)
// 활동 글 작성 권한은 동아리장만 (기획서 §6.1)
const isLeader = computed(() => club.value?.my?.role === '동아리장')

const meeting = computed(() => {
  const c = club.value
  if (!c) return ''
  const when = [c.meet_day, c.meet_time].filter(Boolean).join(' ')
  return [when, c.meet_place].filter(Boolean).join(' · ') || '미정'
})

const founded = computed(() => {
  const y = club.value?.founded_year
  if (!y) return '미상'
  const nth = new Date().getFullYear() - y + 1
  return `${y}년 · 올해 ${nth}년째`
})

const genText = computed(() => {
  const c = club.value
  if (!c?.current_gen) return '—'
  if (c.recruit_status === '상시모집') return `${c.current_gen}기 · 상시 모집`
  if (recruitOpen.value) return `${c.current_gen}기 모집 중`
  return `${c.current_gen}기 · 현재 모집 마감`
})

/* 가입 버튼 — my 가 null 이면 비로그인 (api.md §3) */
const loggedIn = computed(() => !!club.value?.my)
/* 이미 부원이면 모집 상태와 무관하게 잠근다 — 모집중이 아닐 때만 잠그면
   가입한 동아리에서도 버튼이 눌려 "모집중이 아닙니다" 모달이 뜬다 */
const applyDisabled = computed(
  () => loggedIn.value && club.value?.my?.can_apply === false,
)
const applyReason = computed(() => {
  const my = club.value?.my
  if (!my || my.can_apply !== false) return ''
  if (my.is_member) {
    return my.membership === 'OB'
      ? 'OB는 신규 가입 신청을 할 수 없습니다.'
      : '이미 이 동아리의 부원입니다.'
  }
  if (my.join_request_status === '심사중') return '이미 신청했습니다. 동아리장의 승인을 기다리는 중입니다.'
  if (!auth.isVerified) return '이메일 인증을 마치면 신청할 수 있습니다.'
  return '지금은 가입 신청을 할 수 없습니다.'
})

function onApply() {
  if (!recruitOpen.value) { closedDlg.value?.showModal(); return }
  // 로그인은 모달이다 (디자인 기획 §6-2). name:'login' 으로 push 하면 라우터가 '/' 로
  // 리다이렉트해 보던 동아리를 잃는다 — 현재 주소에 ?auth=login 만 붙여 헤더의 모달을 연다.
  if (!loggedIn.value) { router.replace({ path: route.path, query: { ...route.query, auth: 'login' } }); return }
  if (applyDisabled.value) return
  joinDlg.value?.open()
}

async function onSubmitted() {
  applied.value = true
  await load()                 // can_apply · join_request_status 갱신
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    club.value = await api.clubs.detail(props.id)
  } catch (e) {
    loadError.value = e?.status === 404
      ? '동아리를 찾을 수 없습니다.'
      : (e?.message ?? '동아리 정보를 불러오지 못했습니다.')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.id, load)
// 모달에서 로그인하면 화면은 그대로 남는다 — my(가입 가능 여부)를 다시 받아야 버튼이 맞는다
watch(() => auth.isLoggedIn, load)
</script>

<template>
  <div v-if="loading" class="state">불러오는 중…</div>

  <div v-else-if="loadError" class="state">
    <h1 class="page-title">{{ loadError }}</h1>
    <p class="sub">주소를 확인하거나 아카이브에서 다시 찾아보세요.</p>
    <RouterLink class="btn" to="/archive">둘러보기로 가기</RouterLink>
  </div>

  <template v-else-if="club">
    <section class="top" :style="phVars">
      <!-- 동아리명에 섞인 영문만 Inter 로 뜬다 (한글은 뒤 폰트로 넘어간다) -->
      <h1 class="page-title latin">{{ club.name }}</h1>

      <div class="top-grid">
        <div class="photo" :style="club.image ? { backgroundImage: `url(${club.image})` } : null">
          <span v-if="!club.image">{{ emoji }}</span>
        </div>

        <div class="side">
          <div class="acts">
            <!-- 동아리장에게만 보이는 진입점. 없으면 글 작성 화면에 주소를 직접 쳐야 들어간다 -->
            <RouterLink v-if="isLeader" class="btn ghost write" :to="`/clubs/${club.id}/posts/new`">
              활동 글 쓰기
            </RouterLink>
            <!-- disabled 버튼은 마우스 이벤트를 받지 않는다. 감싼 칸이 호버를 대신 받는다 -->
            <span class="apply-slot" :data-tip="applyDisabled ? applyReason : ''">
              <button class="apply" :disabled="applyDisabled" @click="onApply">가입 신청</button>
            </span>
            <button class="members" @click="membersDlg?.open()">인원 <b>{{ memberCount }}</b></button>
          </div>

          <p v-if="applied" class="warn note">
            신청이 접수되었습니다. 결과는 이메일과 ‘내 신청 현황’에서 확인할 수 있습니다.
          </p>
          <p v-else-if="applyDisabled" class="note sub">{{ applyReason }}</p>

          <div class="intro">
            <p v-for="(p, i) in paragraphs" :key="i">{{ p }}</p>
            <p v-if="!paragraphs.length" class="sub">아직 소개글이 없습니다.</p>
          </div>

          <div class="facts">
            <dl>
              <dt>분야</dt>      <dd><span class="tag">{{ club.category }}</span></dd>
              <dt>정기모임</dt>  <dd>{{ meeting }}</dd>
              <dt>창립</dt>      <dd>{{ founded }}</dd>
              <dt>지도교수</dt>  <dd>{{ club.advisor || '—' }}</dd>
              <dt>현재 기수</dt> <dd>{{ genText }}</dd>
            </dl>
          </div>
        </div>
      </div>
    </section>

    <ClubTimeline :club-id="club.id" :category="club.category" />

    <!-- 모달 1 · 가입 신청 -->
    <ClubJoinDialog ref="joinDlg" :club-id="club.id" :club-name="club.name"
                    :current-gen="club.current_gen"
                    @submitted="onSubmitted" @not-recruiting="closedDlg?.showModal()" />

    <!-- 모달 2 · 모집 아님 (narrow) -->
    <dialog ref="closedDlg" class="narrow" @click.self="closedDlg.close()">
      <div class="sheet-hd">
        <h2>현재 모집중이 아닙니다</h2>
        <button class="x" aria-label="닫기" @click="closedDlg.close()">✕</button>
      </div>
      <div class="sheet-bd">
        <p class="lead">
          {{ club.name }}은(는) 지금 신입 부원을 받고 있지 않습니다.
          다음 모집이 열리면 이 페이지에서 바로 신청할 수 있습니다.
        </p>
        <p class="sub">
          보통 매 학기 개강 직후에 모집합니다. 그동안 활동 기록을 둘러보며 어떤 동아리인지 살펴보세요.
        </p>
      </div>
      <div class="sheet-ft">
        <button class="btn" @click="closedDlg.close()">알겠습니다</button>
      </div>
    </dialog>

    <!-- 모달 3 · 인원 -->
    <ClubMembersDialog ref="membersDlg" :club-id="club.id" :club-name="club.name" />
  </template>
</template>

<style scoped>
.state { text-align: center; padding: 90px 20px 120px; color: var(--dim); }
.state .page-title { color: var(--ink); margin: 0 0 8px; }
.state .btn { margin-top: 18px; }

.top { padding: clamp(34px, 6vh, 64px) clamp(20px, 4vw, 56px) clamp(30px, 5vh, 54px); }
.top h1 { margin: 0 auto clamp(26px, 4vh, 44px); text-align: center; }

.top-grid {
  max-width: 1160px; margin: 0 auto;
  display: grid; grid-template-columns: minmax(240px, 34%) 1fr; gap: clamp(26px, 4vw, 56px);
  align-items: start;
}
.photo {
  aspect-ratio: 4 / 5; border-radius: 22px;
  background: linear-gradient(150deg, var(--ph-a), var(--ph-b));
  background-size: cover; background-position: center;
  display: grid; place-items: center; font-size: 3.4rem; border: var(--border);
}
.side { display: flex; flex-direction: column; min-height: 100%; }

.acts { display: flex; gap: 9px; justify-content: flex-end; margin-bottom: 18px; }
.acts .apply {
  background: var(--accent); color: var(--onAccent); border: none;
  border-radius: var(--r-btn); padding: 11px 22px; font: inherit; font-size: 14.5px; font-weight: 700;
  cursor: pointer; transition: filter var(--t-hover);
}
.acts .members {
  background: var(--chip); color: var(--ink); border: var(--border);
  border-radius: var(--r-btn); padding: 11px 18px; font: inherit; font-size: 14.5px; font-weight: 700;
  display: inline-flex; align-items: center; gap: 8px; cursor: pointer;
}
.acts .write { height: auto; padding: 11px 18px; font-size: 14.5px; }
.acts .apply:hover, .acts .members:hover { filter: brightness(.97); }
.acts .apply:disabled { opacity: .45; cursor: not-allowed; filter: none; }

/* 잠긴 이유를 마우스를 올렸을 때만 연하게 띄운다 */
.apply-slot { position: relative; display: inline-flex; }
.apply-slot:not([data-tip=""])::after {
  content: attr(data-tip);
  position: absolute; left: 50%; bottom: calc(100% + 9px);
  transform: translateX(-50%) translateY(4px);
  padding: 7px 12px; border-radius: 10px;
  background: var(--card); border: var(--border);
  box-shadow: 0 6px 18px var(--shadow);
  font-size: 12.5px; font-weight: 600; color: var(--dim);
  white-space: nowrap; pointer-events: none;
  opacity: 0; transition: opacity .18s ease, transform .18s ease;
}
.apply-slot:not([data-tip=""]):hover::after { opacity: .92; transform: translateX(-50%); }

.note { margin: 0 0 16px; }
.note.sub { font-size: 12.5px; }

.intro { font-size: 15px; line-height: 1.9; margin: 0 0 22px; }
.intro p { margin: 0 0 14px; }

.facts { border-top: 1px solid var(--line); margin-top: auto; }
.facts dl { display: grid; grid-template-columns: auto 1fr; gap: 0; margin: 0; }
.facts dt { padding: 11px 0; font-size: 12.5px; color: var(--dim); width: 96px; border-bottom: 1px solid var(--line); }
.facts dd { padding: 11px 0; margin: 0; font-size: 14px; border-bottom: 1px solid var(--line); }
.facts dl > :nth-last-child(-n+2) { border-bottom: none; }

.tag {
  display: inline-block; background: var(--chip); border: 1px solid var(--line);
  border-radius: var(--r-chip); padding: 2px 10px; font-size: 11.5px; color: var(--dim); font-weight: 600;
}

/* 모집 아님 모달 */
dialog { box-shadow: 0 26px 70px var(--shadowUp); }
dialog::backdrop { backdrop-filter: blur(3px); }
.sheet-hd { position: relative; padding: 22px 24px 14px; border-bottom: 1px solid var(--line); }
.sheet-hd h2 { margin: 0; font-size: 19px; letter-spacing: -.025em; }
.sheet-hd .x {
  position: absolute; top: 16px; right: 16px; width: 32px; height: 32px;
  border: none; border-radius: 9px; background: none; color: var(--dim);
  font: inherit; font-size: 18px; display: grid; place-items: center; cursor: pointer;
}
.sheet-hd .x:hover { background: var(--chip); color: var(--ink); }
.sheet-bd { padding: 20px 24px 4px; }
.sheet-bd .lead { margin: 0 0 14px; font-size: 14px; line-height: 1.8; }
.sheet-bd .sub { margin: 0; line-height: 1.75; }
.sheet-ft { display: flex; gap: 9px; padding: 20px 24px 24px; }
.sheet-ft .btn { flex: 1; height: 44px; }

@media (max-width: 900px) {
  .top-grid { grid-template-columns: 1fr; }
  .photo { aspect-ratio: 16 / 10; }
  .acts { justify-content: stretch; }
  .acts .apply-slot { flex: 1; }
  .acts .apply { flex: 1; }
  .apply-slot::after { white-space: normal; max-width: 68vw; }
}
</style>
