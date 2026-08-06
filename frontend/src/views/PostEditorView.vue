<script setup>
/* T5 · 담당 cw — 활동 글 작성/수정
 *
 * 한 컴포넌트가 두 라우트를 처리한다 (router/index.js — 수정하지 않는다):
 *   /clubs/:id/posts/new  name: post-new   → props.id = club id
 *   /posts/:id/edit       name: post-edit  → props.id = post id
 *
 * 계약: api.md §6 (uploads · posts create/update/delete) · §3 GET /posts/{id} · §0.1 에러
 * 기획: 기획서 §6 (공개 기본값 비공개 — 활동 사진에 학생 얼굴이 들어간다)
 * 디자인: 프론트엔드 디자인 기획 §6 남은 페이지 제작 규칙 (목업 없음)
 *
 * ★ 'AI 초안' 자리는 PostEditorAiPanel.vue 에 레이아웃만 만들어 뒀다. T6(wj)이 거기에 꽂는다.
 */
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { ApiError } from '../api'
import { useAuth } from '../stores/auth'
import PostEditorAiPanel from '../components/PostEditorAiPanel.vue'

const props = defineProps({ id: { type: String, required: true } })

const route = useRoute()
const router = useRouter()
const auth = useAuth()

const isEdit = computed(() => route.name === 'post-edit')

const loading = ref(false)
const loadError = ref('')
const denied = ref('')          // can_edit === false 등 권한 안내
const saving = ref(false)
const removing = ref(false)
const formError = ref('')
const missing = ref([])         // 필수 미입력 필드 key

const post = ref(null)          // 수정 모드에서 불러온 원본
const clubId = ref(null)
const clubName = ref('')

const form = reactive({
  title: '',
  body: '',
  activity_date: '',
  tagsText: '',
  is_public: false,             // ★ 기본 비공개 (기획서 §6.1)
})

/* 사진 — 업로드는 글 저장과 분리돼 있다 (api.md §6). 한 장씩 올려 url 만 모은다. */
let photoSeq = 0
const photos = ref([])          // { key, name, url, status: 'uploading'|'done'|'error', error }
const fileInput = ref(null)
const removeDlg = ref(null)

const MAX_BYTES = 10 * 1024 * 1024
const OK_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const doneUrls = computed(() => photos.value.filter((p) => p.status === 'done').map((p) => p.url))
const uploading = computed(() => photos.value.some((p) => p.status === 'uploading'))

const tags = computed(() =>
  form.tagsText.split(',').map((t) => t.trim().replace(/^#/, '')).filter(Boolean),
)

const heading = computed(() => (isEdit.value ? '활동 글 수정' : '활동 글 쓰기'))
const subheading = computed(() =>
  clubName.value ? `${clubName.value} · 동아리장만 작성할 수 있습니다` : '동아리장만 작성할 수 있습니다',
)

const backTo = computed(() =>
  isEdit.value && post.value ? `/posts/${post.value.id}` : (clubId.value ? `/clubs/${clubId.value}` : '/archive'),
)

/* --- 불러오기 ----------------------------------------------------- */

async function load() {
  loadError.value = ''
  denied.value = ''
  formError.value = ''

  if (!isEdit.value) {
    clubId.value = props.id
    clubName.value = ''
    loading.value = true
    try {
      const club = await api.clubs.detail(props.id)
      clubName.value = club?.name ?? ''
      if (club?.my && club.my.role !== '동아리장' && !auth.isAdmin) {
        denied.value = '이 동아리의 동아리장만 활동 글을 쓸 수 있습니다.'
      }
    } catch (e) {
      // 동아리 이름은 부가 정보다. 못 읽어도 작성 자체는 막지 않는다.
      if (e instanceof ApiError && e.status === 404) loadError.value = '동아리를 찾을 수 없습니다.'
    } finally {
      loading.value = false
    }
    return
  }

  loading.value = true
  try {
    const p = await api.posts.detail(props.id)
    post.value = p
    clubId.value = p.club_id
    clubName.value = p.club_name ?? ''
    if (p.can_edit === false) {
      denied.value = '이 글을 수정할 권한이 없습니다. 작성한 동아리의 동아리장만 고칠 수 있습니다.'
      return
    }
    form.title = p.title ?? ''
    form.body = p.body ?? ''
    form.activity_date = p.activity_date ?? ''
    form.tagsText = (p.tags ?? []).join(', ')
    form.is_public = !!p.is_public
    photos.value = (p.photos ?? []).map((url) => ({
      key: `p${photoSeq++}`, name: url.split('/').pop(), url, status: 'done', error: '',
    }))
  } catch (e) {
    loadError.value = e instanceof ApiError && e.status === 404
      ? '글을 찾을 수 없습니다. 삭제되었거나 볼 권한이 없습니다.'
      : (e?.message ?? '글을 불러오지 못했습니다.')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => [route.name, props.id], load)

/* --- 사진 업로드 --------------------------------------------------- */

function pickFiles() { fileInput.value?.click() }

async function onFiles(e) {
  const files = Array.from(e.target.files ?? [])
  e.target.value = ''                       // 같은 파일 다시 고를 수 있게
  for (const file of files) await uploadOne(file)
}

async function uploadOne(file) {
  const item = reactive({
    key: `p${photoSeq++}`, name: file.name, url: '', status: 'uploading', error: '', file,
  })
  photos.value.push(item)

  if (!OK_TYPES.includes(file.type)) {
    item.status = 'error'
    item.error = 'jpg · png · webp 이미지만 올릴 수 있습니다.'
    return
  }
  if (file.size > MAX_BYTES) {
    item.status = 'error'
    item.error = '10MB 이하 이미지만 올릴 수 있습니다.'
    return
  }

  try {
    const r = await api.upload(file)
    item.url = r?.url ?? ''
    item.status = item.url ? 'done' : 'error'
    if (!item.url) item.error = '업로드 주소를 받지 못했습니다.'
  } catch (err) {
    item.status = 'error'
    item.error = err?.message ?? '사진을 올리지 못했습니다.'
  }
}

function retry(item) {
  if (!item.file) return
  photos.value = photos.value.filter((p) => p.key !== item.key)
  uploadOne(item.file)
}

function removePhoto(key) {
  photos.value = photos.value.filter((p) => p.key !== key)
}

/* --- 저장 ---------------------------------------------------------- */

function validate() {
  const m = []
  if (!form.title.trim()) m.push('title')
  if (!form.body.trim()) m.push('body')
  if (!form.activity_date) m.push('activity_date')
  missing.value = m
  return m.length === 0
}

async function save() {
  formError.value = ''
  if (!validate()) {
    formError.value = '제목 · 본문 · 활동 날짜는 반드시 채워 주세요.'
    return
  }
  if (uploading.value) {
    formError.value = '사진 업로드가 끝난 뒤에 저장할 수 있습니다.'
    return
  }

  const payload = {
    title: form.title.trim(),
    body: form.body,
    photos: doneUrls.value,
    activity_date: form.activity_date,
    tags: tags.value,
    is_public: form.is_public,
  }

  saving.value = true
  try {
    const saved = isEdit.value
      ? await api.posts.update(props.id, payload)
      : await api.posts.create(clubId.value, payload)
    const id = saved?.id ?? props.id
    router.push(`/posts/${id}`)
  } catch (e) {
    if (e instanceof ApiError && e.code === 'EMAIL_NOT_VERIFIED') {
      formError.value = `${e.message} 이메일 인증을 마친 뒤 다시 시도해 주세요.`
    } else if (e instanceof ApiError && (e.code === 'FORBIDDEN' || e.status === 403)) {
      formError.value = e.message
    } else if (e instanceof ApiError && e.status === 404) {
      formError.value = '대상을 찾을 수 없습니다. 주소를 확인해 주세요.'
    } else {
      formError.value = e?.message ?? '글을 저장하지 못했습니다.'
    }
  } finally {
    saving.value = false
  }
}

/* --- 삭제 (수정 모드만) — 네이티브 confirm() 대신 <dialog> 확인 시트 (디자인 §6-2) --- */

function askRemove() {
  formError.value = ''
  removeDlg.value?.showModal()
}

async function confirmRemove() {
  removing.value = true
  try {
    await api.posts.remove(props.id)
    removeDlg.value?.close()
    router.push(clubId.value ? `/clubs/${clubId.value}` : '/archive')
  } catch (e) {
    removeDlg.value?.close()
    formError.value = e?.message ?? '글을 삭제하지 못했습니다.'
  } finally {
    removing.value = false
  }
}

/* T6(wj)이 PostEditorAiPanel 에서 emit 할 자리. 지금은 호출되지 않는다. */
function applyDraft(draft) {
  if (!draft) return
  if (draft.title) form.title = draft.title
  if (draft.body) form.body = draft.body
  if (draft.tags?.length) form.tagsText = draft.tags.join(', ')
}
</script>

<template>
  <div class="wrap container">
    <div v-if="loading" class="state">불러오는 중…</div>

    <div v-else-if="loadError" class="state">
      <h1 class="page-title">{{ loadError }}</h1>
      <p class="sub">주소를 확인하거나 아카이브에서 다시 찾아보세요.</p>
      <RouterLink class="btn" to="/archive">둘러보기로 가기</RouterLink>
    </div>

    <div v-else-if="denied" class="state">
      <h1 class="page-title">권한이 없습니다</h1>
      <p class="sub">{{ denied }}</p>
      <RouterLink class="btn" :to="backTo">돌아가기</RouterLink>
    </div>

    <template v-else>
      <header class="hd">
        <p class="eyebrow">{{ isEdit ? 'EDIT POST' : 'NEW POST' }}</p>
        <h1 class="page-title">{{ heading }}</h1>
        <p class="sub">{{ subheading }}</p>
      </header>

      <!-- ★ AI 초안 자리 — 레이아웃만 완성돼 있다. T6(wj)이 여기에 기능을 꽂는다. -->
      <PostEditorAiPanel :club-id="clubId" :has-key="auth.hasAiKey" @draft="applyDraft" />

      <form class="form card" novalidate @submit.prevent="save">
        <div class="fld">
          <label for="pe-title">제목<span class="req">*</span></label>
          <input id="pe-title" v-model="form.title" :class="{ bad: missing.includes('title') }"
                 placeholder="성북동 출사, 필름 두 롤" maxlength="120">
        </div>

        <div class="fld">
          <label for="pe-body">본문<span class="req">*</span></label>
          <textarea id="pe-body" v-model="form.body" :class="{ bad: missing.includes('body') }"
                    placeholder="언제 · 어디서 · 누가 · 무엇을 했는지 적어 주세요."></textarea>
          <p class="hint">줄바꿈만 반영되는 평문입니다. 마크다운은 쓰지 않습니다.</p>
        </div>

        <div class="row">
          <div class="fld">
            <label for="pe-date">활동 날짜<span class="req">*</span></label>
            <input id="pe-date" v-model="form.activity_date" type="date"
                   :class="{ bad: missing.includes('activity_date') }">
            <p class="hint">글을 올린 날이 아니라 실제 활동한 날입니다.</p>
          </div>

          <div class="fld">
            <label for="pe-tags">태그</label>
            <input id="pe-tags" v-model="form.tagsText" placeholder="출사, 필름, 성북동">
            <p class="hint">
              쉼표로 구분합니다.
              <span v-if="tags.length">— {{ tags.length }}개: {{ tags.join(' · ') }}</span>
            </p>
          </div>
        </div>

        <div class="fld">
          <label id="pe-photos-label">사진</label>
          <div class="dropzone">
            <button type="button" class="btn ghost" @click="pickFiles">사진 고르기</button>
            <p class="hint">jpg · png · webp, 한 장에 10MB까지. 여러 장 한 번에 고를 수 있습니다.</p>
            <input ref="fileInput" class="sr" type="file" accept="image/jpeg,image/png,image/webp"
                   multiple aria-labelledby="pe-photos-label" @change="onFiles">
          </div>

          <ul v-if="photos.length" class="shots">
            <li v-for="(p, i) in photos" :key="p.key" class="shot" :class="p.status">
              <div class="thumb" :style="p.url ? { backgroundImage: `url(${p.url})` } : null">
                <span v-if="p.status === 'uploading'" class="badge">올리는 중…</span>
                <span v-else-if="p.status === 'error'" class="badge">실패</span>
                <span v-else-if="i === 0" class="badge cover">대표</span>
              </div>
              <div class="meta">
                <p class="name">{{ p.name }}</p>
                <p v-if="p.error" class="err">{{ p.error }}</p>
              </div>
              <div class="acts">
                <button v-if="p.status === 'error' && p.file" type="button" class="btn ghost sm"
                        @click="retry(p)">다시 시도</button>
                <button type="button" class="btn ghost sm" @click="removePhoto(p.key)">삭제</button>
              </div>
            </li>
          </ul>
          <p class="hint">맨 앞 사진이 목록·캐러셀에 걸리는 대표 사진입니다.</p>
        </div>

        <div class="fld toggle">
          <label class="switch" for="pe-public">
            <input id="pe-public" v-model="form.is_public" type="checkbox">
            <span>공개 글로 올리기</span>
          </label>
          <p class="hint">
            활동 사진에는 학생 얼굴이 들어가기 때문에 기본값은 비공개입니다.
            공개하면 비로그인 사용자에게도 사진과 본문이 그대로 보입니다.
          </p>
          <p class="privacy">
            <span>🔒</span>
            <span>비공개 글은 이 동아리 소속(부원 · OB · 동아리장)과 관리자에게만 보입니다.</span>
          </p>
        </div>

        <p v-if="formError" class="warn">{{ formError }}</p>

        <div class="ft">
          <RouterLink class="btn ghost" :to="backTo">취소</RouterLink>
          <button v-if="isEdit" type="button" class="btn ghost danger" @click="askRemove">글 삭제</button>
          <button type="submit" class="btn" :disabled="saving || uploading">
            {{ saving ? '저장 중…' : (isEdit ? '수정 저장' : (form.is_public ? '공개로 올리기' : '비공개로 올리기')) }}
          </button>
        </div>
      </form>
    </template>

    <!-- 삭제 확인 — 브라우저 confirm() 대신 네이티브 <dialog> (디자인 §6-2) -->
    <dialog ref="removeDlg" class="narrow" @click.self="removeDlg.close()">
      <div class="sheet-hd">
        <h2>이 글을 삭제할까요?</h2>
        <button class="x" aria-label="닫기" @click="removeDlg.close()">✕</button>
      </div>
      <div class="sheet-bd">
        <p class="lead">{{ form.title || '제목 없는 글' }}</p>
        <p class="sub">삭제하면 되돌릴 수 없습니다. 올린 사진도 글과 함께 보이지 않게 됩니다.</p>
      </div>
      <div class="sheet-ft">
        <button class="btn ghost" @click="removeDlg.close()">취소</button>
        <button class="btn danger" :disabled="removing" @click="confirmRemove">
          {{ removing ? '삭제 중…' : '삭제하기' }}
        </button>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
.wrap { padding: clamp(28px, 5vh, 56px) 0 clamp(48px, 8vh, 96px); max-width: 860px; }

.state { text-align: center; padding: 80px 20px 110px; color: var(--dim); }
.state .page-title { color: var(--ink); margin: 0 0 8px; font-size: clamp(24px, 4vw, 34px); }
.state .btn { margin-top: 18px; }

.hd { margin-bottom: 22px; }
.hd .eyebrow { margin: 0 0 6px; }
.hd .page-title { margin: 0 0 6px; font-size: clamp(26px, 4.4vw, 40px); }
.hd .sub { margin: 0; }

.form { margin-top: 18px; padding: 22px; }
.form:hover { box-shadow: 0 5px 16px var(--shadow); transform: none; }

.fld { margin-bottom: 18px; }
.fld:last-of-type { margin-bottom: 0; }
.fld textarea { min-height: 220px; resize: vertical; line-height: 1.85; }
.fld .bad { border-color: var(--warnLine); }

.row { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }

/* 사진 */
.sr { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
.dropzone {
  border: 1.5px dashed var(--line); border-radius: var(--r-input);
  padding: 18px; text-align: center; background: var(--bg);
}
.dropzone .hint { margin-top: 8px; }

.shots { list-style: none; margin: 12px 0 6px; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.shot {
  display: grid; grid-template-columns: 72px 1fr auto; gap: 12px; align-items: center;
  border: var(--border); border-radius: 14px; padding: 8px; background: var(--card);
}
.shot.error { border-color: var(--warnLine); }
.thumb {
  position: relative; width: 72px; height: 54px; border-radius: 10px;
  background: var(--chip) center / cover no-repeat;
}
.badge {
  position: absolute; left: 4px; bottom: 4px;
  padding: 1px 7px; border-radius: var(--r-chip);
  background: var(--scrim); color: var(--onAccent);
  font-size: 10.5px; font-weight: 700;
}
.badge.cover { background: var(--accent); }
.meta { min-width: 0; }
.meta .name { margin: 0; font-size: 13px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta .err { margin: 2px 0 0; font-size: 12px; color: var(--warnInk); }
.acts { display: flex; gap: 6px; }
.btn.sm { height: 32px; padding: 0 11px; font-size: 12.5px; }

/* 공개 토글 */
.toggle { border-top: 1px solid var(--line); padding-top: 18px; }
.switch { display: flex; align-items: center; gap: 9px; margin: 0; cursor: pointer; font-size: 14px; }
.switch input { width: 18px; height: 18px; accent-color: var(--accent); flex: none; }
.toggle .privacy { display: flex; gap: 9px; align-items: flex-start; margin: 12px 0 0; line-height: 1.65; }

.warn { margin: 18px 0 0; }

.ft { display: flex; gap: 9px; justify-content: flex-end; margin-top: 22px; }
.ft .btn { height: 44px; }
.btn.danger { color: var(--warnInk); border-color: var(--warnLine); background: var(--warnBg); }

/* 삭제 확인 시트 */
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
.sheet-bd .lead { margin: 0 0 10px; font-size: 14px; font-weight: 700; line-height: 1.7; }
.sheet-bd .sub { margin: 0; line-height: 1.75; }
.sheet-ft { display: flex; gap: 9px; padding: 20px 24px 24px; }
.sheet-ft .btn { flex: 1; height: 44px; }

@media (max-width: 720px) {
  .row { grid-template-columns: 1fr; gap: 0; }
  .ft { flex-wrap: wrap; }
  .ft .btn { flex: 1; }
}
</style>
