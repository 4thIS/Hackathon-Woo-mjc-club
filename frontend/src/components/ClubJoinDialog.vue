<script setup>
/* 가입 신청 모달 — 디자인 기획 §5.3 모달1
 * api.md §4: GET /clubs/{id}/join-form → { required, fields[] }, fields 가 비면 폼 없이 바로 신청.
 *            POST /clubs/{id}/join-requests { answers } */
import { ref, reactive, computed } from 'vue'
import api, { ApiError } from '../api'

const props = defineProps({
  clubId: { type: [String, Number], required: true },
  clubName: { type: String, default: '' },
  currentGen: { type: Number, default: null },
})
const emit = defineEmits(['submitted', 'not-recruiting'])

const dlg = ref(null)
const fields = ref([])
const formRequired = ref(false)
const answers = reactive({})
const loading = ref(false)
const sending = ref(false)
const error = ref('')
const loaded = ref(false)

const subtitle = computed(() => {
  const gen = props.currentGen ? `${props.currentGen}기 · ` : ''
  return `${gen}동아리장이 확인 후 승인합니다`
})

async function loadForm() {
  if (loaded.value) return
  loading.value = true
  try {
    const r = await api.joinForm.get(props.clubId)
    formRequired.value = !!r?.required
    fields.value = r?.fields ?? []
    fields.value.forEach((f) => { if (answers[f.key] === undefined) answers[f.key] = '' })
    loaded.value = true
  } catch {
    // 가입폼을 못 읽어도 신청 자체는 막지 않는다 (폼 없이 진행)
    fields.value = []
    formRequired.value = false
  } finally {
    loading.value = false
  }
}

function open() {
  error.value = ''
  dlg.value?.showModal()
  loadForm()
}
defineExpose({ open })

const missing = computed(() =>
  fields.value.filter((f) => (f.required || formRequired.value) && !String(answers[f.key] ?? '').trim()),
)

async function submit() {
  error.value = ''
  if (missing.value.length) {
    error.value = `필수 항목을 채워주세요 — ${missing.value.map((f) => f.label).join(', ')}`
    return
  }
  sending.value = true
  try {
    const payload = {}
    fields.value.forEach((f) => { payload[f.key] = answers[f.key] ?? '' })
    await api.joinRequests.create(props.clubId, payload)
    dlg.value?.close()
    emit('submitted')
  } catch (e) {
    if (e instanceof ApiError && e.code === 'CLUB_NOT_RECRUITING') {
      dlg.value?.close()
      emit('not-recruiting')            // 모집 아님 모달로 넘긴다 (디자인 §5.3 모달2)
      return
    }
    error.value = e?.message ?? '신청을 처리하지 못했습니다.'
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <dialog ref="dlg" @click.self="dlg.close()">
    <div class="sheet-hd">
      <h2>{{ clubName }} 가입 신청</h2>
      <p>{{ subtitle }}</p>
      <button class="x" aria-label="닫기" @click="dlg.close()">✕</button>
    </div>

    <div class="sheet-bd">
      <p v-if="loading" class="sub">가입폼을 불러오는 중…</p>

      <template v-else>
        <div v-for="(f, i) in fields" :key="f.key" class="fld">
          <label :for="`jf-${f.key}`">
            {{ f.label }}<span v-if="f.required || formRequired" class="req">*</span>
          </label>
          <textarea v-if="f.type === 'textarea'" :id="`jf-${f.key}`" v-model="answers[f.key]"
                    placeholder="자유롭게 적어주세요"></textarea>
          <input v-else :id="`jf-${f.key}`" v-model="answers[f.key]" placeholder="자유롭게 적어주세요">
          <p v-if="i === fields.length - 1" class="hint">이 질문들은 동아리장이 직접 만든 가입폼입니다.</p>
        </div>

        <p v-if="!fields.length" class="no-form">
          이 동아리는 별도 가입폼이 없습니다. 바로 신청할 수 있습니다.
        </p>

        <p v-if="error" class="warn err">{{ error }}</p>

        <p class="privacy">
          <span>🔒</span>
          <span>동아리장에게는 <b>이름 · 학과 · 학년</b>과 위 답변만 전달됩니다.
            학번 전체 · 생년월일 · 성별은 전달되지 않습니다.</span>
        </p>
      </template>
    </div>

    <div class="sheet-ft">
      <button class="btn ghost" @click="dlg.close()">취소</button>
      <button class="btn" :disabled="sending || loading" @click="submit">
        {{ sending ? '신청 중…' : '신청하기' }}
      </button>
    </div>
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
  font: inherit; font-size: 18px; display: grid; place-items: center; cursor: pointer;
}
.sheet-hd .x:hover { background: var(--chip); color: var(--ink); }

.sheet-bd { padding: 20px 24px 24px; }
.sheet-ft { display: flex; gap: 9px; padding: 0 24px 24px; }
.sheet-ft .btn { flex: 1; height: 44px; }

.fld { margin-bottom: 16px; }
.fld textarea { min-height: 88px; resize: vertical; }
.no-form { margin: 0 0 16px; font-size: 14px; line-height: 1.8; color: var(--dim); }
.err { margin: 0 0 16px; }
.privacy { display: flex; gap: 9px; align-items: flex-start; margin: 0; line-height: 1.65; }
.privacy b { color: var(--ink); }
</style>
