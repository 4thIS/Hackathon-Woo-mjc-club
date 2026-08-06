<script setup>
/* 백엔드가 /api/auth/verify 처리 후 여기로 302 시킨다 → ?status=ok|expired|invalid */
import { useRoute } from 'vue-router'
import PagePlaceholder from '../components/PagePlaceholder.vue'

const route = useRoute()
</script>

<template>
  <PagePlaceholder
    title="이메일 인증"
    task="T1"
    owner="wj"
    :spec="`api.md §2 — status=${route.query.status ?? '(없음)'}`" />
</template>
