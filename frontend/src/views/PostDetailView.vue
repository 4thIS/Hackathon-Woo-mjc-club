<script setup>
import PagePlaceholder from '../components/PagePlaceholder.vue'
defineProps({ id: { type: String, required: true } })
</script>

<template>
  <PagePlaceholder
    title="활동 글"
    task="T5"
    owner="cw"
    spec="api.md §3 GET /api/posts/{id} — 비공개 글은 무권한 시 404" />
</template>
