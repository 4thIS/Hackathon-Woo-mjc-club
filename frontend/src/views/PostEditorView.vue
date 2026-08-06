<script setup>
/* T5 · 담당 cw — 활동 글 작성/수정.
   ★ 'AI 초안' 버튼 자리를 비워 둔다. T6(wj)이 여기에 꽂는다 (구현계획 T5). */
import PagePlaceholder from '../components/PagePlaceholder.vue'
defineProps({ id: { type: String, default: '' } })
</script>

<template>
  <PagePlaceholder
    title="활동 글 작성"
    task="T5 (+T6 AI 초안 버튼)"
    owner="cw / wj"
    spec="api.md §6 · §7 — 공개 토글 기본 false, 키 없으면 AI 버튼 비활성 + 안내" />
</template>
