<script setup>
/* T3 · 담당 th. 명세: docs/api.md §4, 디자인 기획 §5.3 모달 1·2
 *
 * club.html 상세 페이지의 "가입 신청" 버튼에서 연다:
 *   const modal = ref(null)
 *   <JoinRequestModal ref="modal" :club-id="club.id" @applied="onApplied" />
 *   <button @click="modal.open()">가입 신청</button>
 */
import { ref } from 'vue'
import api, { ApiError } from '../api'

const props = defineProps({ clubId: { type: [Number, String], required: true } })
const emit = defineEmits(['applied'])

const dialog = ref(null)
const notRecruiting = ref(null) // narrow 시트 열기 전에 잠깐 보여줌
const loading = ref(false)
const submitting = ref(false)
const error = ref('')
const form = ref({ required: false, fields: [] })
const answers = ref({})

async function open() {
  error.value = ''
  answers.value = {}
  notRecruiting.value = false
  loading.value = true
  dialog.value.showModal()
  try {
    form.value = await api.joinForm.get(props.clubId)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function close() {
  dialog.value.close()
}

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const res = await api.joinRequests.create(props.clubId, answers.value)
    emit('applied', res)
    close()
  } catch (e) {
    if (e instanceof ApiError && e.code === 'CLUB_NOT_RECRUITING') {
      notRecruiting.value = true
    } else {
      error.value = e.message
    }
  } finally {
    submitting.value = false
  }
}

defineExpose({ open, close })
</script>

<template>
  <dialog ref="dialog" :class="{ narrow: notRecruiting }" @click.self="close">
    <div v-if="notRecruiting" class="sheet">
      <header class="sheet-head">
        <h2 class="section-title">모집중이 아니에요</h2>
        <button class="btn ghost icon" @click="close" aria-label="닫기">✕</button>
      </header>
      <div class="sheet-body">
        <p class="sub">이 동아리는 현재 모집중이 아닙니다. 다음 모집을 기다려주세요.</p>
      </div>
      <div class="sheet-actions">
        <button class="btn" @click="close">확인</button>
      </div>
    </div>

    <div v-else class="sheet">
      <header class="sheet-head">
        <h2 class="section-title">가입 신청</h2>
        <button class="btn ghost icon" @click="close" aria-label="닫기">✕</button>
      </header>

      <div class="sheet-body">
        <p v-if="loading" class="sub">불러오는 중…</p>
        <template v-else>
          <p class="privacy">🔒 신청 시 동아리장에게 이름·학과·학년만 전달됩니다.</p>

          <div v-if="error" class="warn">{{ error }}</div>

          <div v-for="f in form.fields" :key="f.key" class="field">
            <label>{{ f.label }} <span v-if="f.required" class="req">*</span></label>
            <textarea
              v-if="f.type === 'textarea'"
              v-model="answers[f.key]"
              rows="3"
              :required="f.required" />
            <input v-else type="text" v-model="answers[f.key]" :required="f.required" />
          </div>

          <p v-if="form.fields.length === 0" class="sub">이 동아리는 별도 가입폼이 없습니다.</p>
        </template>
      </div>

      <div class="sheet-actions">
        <button class="btn ghost" @click="close">취소</button>
        <button class="btn" :disabled="loading || submitting" @click="submit">신청하기</button>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.sheet-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px; border-bottom: var(--border);
  position: sticky; top: 0; background: var(--card); border-radius: var(--r-sheet) var(--r-sheet) 0 0;
}
.sheet-body { padding: 18px 20px; display: flex; flex-direction: column; gap: 14px; }
.sheet-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 20px; border-top: var(--border); }
.field label { margin-bottom: 6px; }
</style>
