<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="container empty">
    <h1 class="page-title">찾는 페이지가 없어요</h1>
    <p class="sub">주소를 다시 확인해주세요.</p>
    <RouterLink to="/" class="btn">홈으로</RouterLink>
  </section>
</template>

<style scoped>
.empty { padding: 100px 0 140px; }
.sub { margin-bottom: 20px; }
</style>
