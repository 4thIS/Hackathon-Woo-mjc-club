<script setup>
/* T4 · 담당 th. 명세: docs/api.md §5 POST /api/club-applications
 * 승인되면 신청자가 곧 동아리장 1기가 된다 — 개설 화면은 별도 인원 초대 없이 신청 폼만 받는다.
 */
import { reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../api'
import { CATEGORY_NAMES as CATEGORIES } from '../components/ClubCategory'

const form = reactive({
  name: '',
  category: CATEGORIES[0],
  founded_year: new Date().getFullYear(),
  purpose: '',
  advisor: '',
})

const submitting = ref(false)
const error = ref('')
const result = ref(null) // { id, status }

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

async function cancel() {
  if (!result.value) return
  await api.clubApplications.cancel(result.value.id)
  result.value = null
}
</script>

<template>
  <section class="container page">
    <p class="eyebrow">T4 · 동아리 개설</p>
    <h1 class="page-title">동아리 개설 신청</h1>
    <p class="sub">승인되면 신청자 본인이 동아리장 1기가 됩니다.</p>

    <div v-if="result" class="card done">
      <p class="section-title">신청이 접수됐어요</p>
      <p class="sub">현재 상태: {{ result.status }} — 관리자 승인을 기다려주세요.</p>
      <button class="btn ghost" @click="cancel">신청 취소</button>
    </div>

    <form v-else class="card form" @submit.prevent="submit">
      <div v-if="error" class="warn">{{ error }}</div>

      <div class="row">
        <label>동아리명 <span class="req">*</span></label>
        <input v-model.trim="form.name" required maxlength="60" />
      </div>

      <div class="row">
        <label>분야 <span class="req">*</span></label>
        <select v-model="form.category">
          <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>

      <div class="row">
        <label>창립년도 <span class="req">*</span></label>
        <input v-model.number="form.founded_year" type="number" min="1970" :max="new Date().getFullYear()" required />
      </div>

      <div class="row">
        <label>지도교수</label>
        <input v-model.trim="form.advisor" maxlength="40" />
      </div>

      <div class="row">
        <label>소개</label>
        <textarea v-model.trim="form.purpose" rows="4" placeholder="어떤 활동을 하는 동아리인가요?" />
      </div>

      <button class="btn" type="submit" :disabled="submitting">신청하기</button>
    </form>

    <RouterLink to="/archive" class="btn ghost back">둘러보기로 돌아가기</RouterLink>
  </section>
</template>

<style scoped>
.page { padding: 56px 0 120px; max-width: 640px; }
.card.form, .card.done { padding: 24px; margin-top: 20px; display: flex; flex-direction: column; gap: 16px; }
.card.done { align-items: flex-start; }
.back { margin-top: 24px; }
</style>
