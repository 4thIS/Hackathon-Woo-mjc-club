<script setup>
import PagePlaceholder from '../components/PagePlaceholder.vue'
defineProps({ id: { type: String, required: true } })
</script>

<template>
  <PagePlaceholder
    title="동아리 관리"
    task="T3 · T4"
    owner="th"
    spec="가입폼 편집 · 신청자 목록(이름·학과·학년만) · 부원 관리(기수) · 탈퇴 요청 · 위임 — api.md §4" />
</template>
