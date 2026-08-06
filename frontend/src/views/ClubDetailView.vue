<script setup>
import PagePlaceholder from '../components/PagePlaceholder.vue'
defineProps({ id: { type: String, required: true } })
</script>

<template>
  <PagePlaceholder
    title="동아리 상세"
    task="T2"
    owner="cw"
    spec="디자인 기획 §5.3 (타임라인 5건 배치 로드 · 모달 3종) · api.md §3 GET /api/clubs/{id}" />
</template>
