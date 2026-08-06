<script setup>
/* T0 뼈대의 빈 화면 자리. 담당자가 화면을 만들면서 이 컴포넌트를 지운다. */
defineProps({
  title: { type: String, required: true },
  task: { type: String, default: '' },
  owner: { type: String, default: '' },
  spec: { type: String, default: '' },
})
</script>

<template>
  <section class="container placeholder">
    <p class="eyebrow">{{ task }} · 담당 {{ owner }}</p>
    <h1 class="page-title">{{ title }}</h1>
    <p class="sub">아직 만들지 않은 화면입니다.</p>
    <p v-if="spec" class="hint">명세: {{ spec }}</p>
  </section>
</template>

<style scoped>
.placeholder { padding: 80px 0 120px; }
.page-title { margin: 6px 0 10px; }
</style>
