<script setup>
/* 동아리 개설 신청 — 디자인 기획 §6-2 ("모달은 전부 <dialog>")
 * 명세: docs/api.md §5 POST /api/club-applications
 * 승인되면 신청자가 곧 동아리장 1기가 된다 — 별도 인원 초대 없이 신청 폼만 받는다.
 */
import { reactive, ref } from 'vue'
import api from '../api'
import { CATEGORY_NAMES as CATEGORIES } from './ClubCategory'

const THIS_YEAR = new Date().getFullYear()

const dlg = ref(null)
const submitting = ref(false)
const error = ref('')
const result = ref(null)          // { id, status }

const form = reactive({
  name: '',
  category: CATEGORIES[0],
  founded_year: THIS_YEAR,
  purpose: '',
  advisor: '',
})

function reset() {
  Object.assign(form, {
    name: '', category: CATEGORIES[0], founded_year: THIS_YEAR, purpose: '', advisor: '',
  })
  error.value = ''
  result.value = null
}

function open() {
  reset()
  if (!dlg.value?.open) dlg.value?.showModal()
}
defineExpose({ open })

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    result.value = await api.clubApplications.create({ ...form })
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

async function cancelApplication() {
  if (!result.value) return
  try {
    await api.clubApplications.cancel(result.value.id)
    dlg.value?.close()
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <dialog ref="dlg" @click.self="dlg.close()">
    <!-- 접수 완료 -->
    <template v-if="result">
      <div class="sheet-hd">
        <h2>신청이 접수됐습니다</h2>
        <p>관리자 승인을 기다려주세요.</p>
        <button class="x" aria-label="닫기" @click="dlg.close()">✕</button>
      </div>
      <div class="sheet-bd">
        <p class="msg">
          현재 상태는 <b>{{ result.status }}</b> 입니다. 결과는 <b>내 정보 → 내 신청 현황</b>에서
          확인할 수 있습니다. 승인되면 신청하신 분이 동아리장 1기가 됩니다.
        </p>
        <p v-if="error" class="warn">{{ error }}</p>
      </div>
      <div class="sheet-ft">
        <button class="btn ghost danger" @click="cancelApplication">신청 취소</button>
        <button class="btn" @click="dlg.close()">확인</button>
      </div>
    </template>

    <!-- 신청 폼 -->
    <template v-else>
      <div class="sheet-hd">
        <h2>동아리 개설 신청</h2>
        <p>승인되면 신청하신 분이 동아리장 1기가 됩니다.</p>
        <button class="x" aria-label="닫기" @click="dlg.close()">✕</button>
      </div>

      <form class="sheet-bd" @submit.prevent="submit">
        <p v-if="error" class="warn">{{ error }}</p>

        <div class="fld">
          <label for="ca-name">동아리명<span class="req">*</span></label>
          <input id="ca-name" v-model.trim="form.name" maxlength="60" required
                 placeholder="필름사진동아리 그늘">
        </div>

        <div class="two">
          <div class="fld">
            <label for="ca-cat">분야<span class="req">*</span></label>
            <select id="ca-cat" v-model="form.category">
              <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div class="fld">
            <label for="ca-year">창립년도<span class="req">*</span></label>
            <input id="ca-year" v-model.number="form.founded_year" type="number"
                   min="1970" :max="THIS_YEAR" required>
          </div>
        </div>

        <div class="fld">
          <label for="ca-advisor">지도교수</label>
          <input id="ca-advisor" v-model.trim="form.advisor" maxlength="40" placeholder="아직 없으면 비워두세요">
        </div>

        <div class="fld">
          <label for="ca-purpose">소개</label>
          <textarea id="ca-purpose" v-model.trim="form.purpose" rows="4"
                    placeholder="어떤 활동을 하는 동아리인가요?"></textarea>
          <p class="hint">동아리 상세 화면에 그대로 실립니다. 나중에 고칠 수 있습니다.</p>
        </div>

        <button class="sr-submit" type="submit" aria-hidden="true" tabindex="-1"></button>
      </form>

      <div class="sheet-ft">
        <button class="btn ghost" @click="dlg.close()">취소</button>
        <button class="btn" :disabled="submitting || !form.name" @click="submit">
          {{ submitting ? '신청 중…' : '신청하기' }}
        </button>
      </div>
    </template>
  </dialog>
</template>

<style scoped>
.sheet-hd {
  position: relative;
  padding: 22px 52px 16px 24px;
  border-bottom: 1px solid var(--line);
}
.sheet-hd h2 { margin: 0; font-size: 19px; font-weight: 700; letter-spacing: -.025em; }
.sheet-hd p { margin: 6px 0 0; font-size: 13px; color: var(--dim); }
.sheet-hd .x {
  position: absolute; right: 14px; top: 16px;
  width: 32px; height: 32px; border-radius: 9px;
  border: none; background: none; color: var(--dim);
  font: inherit; font-size: 15px; cursor: pointer;
}
.sheet-hd .x:hover { background: var(--chip); color: var(--ink); }

.sheet-bd { padding: 20px 24px; display: flex; flex-direction: column; gap: 15px; }
.sheet-bd .msg { margin: 0; font-size: 14px; line-height: 1.85; }

.fld { margin: 0; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.sheet-ft {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 16px 24px 20px; border-top: 1px solid var(--line);
}
.btn.ghost.danger { color: var(--dangerInk); border-color: var(--dangerLine); background: var(--dangerBg); }

/* Enter 로 제출되게만 두고 화면에서는 감춘다 (실제 버튼은 푸터에 있다) */
.sr-submit { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }

@media (max-width: 560px) {
  .two { grid-template-columns: 1fr; }
}
</style>
