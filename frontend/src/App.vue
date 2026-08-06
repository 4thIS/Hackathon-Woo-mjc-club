<script setup>
import { RouterView } from 'vue-router'
import SiteHeader from './components/SiteHeader.vue'
import SiteFooter from './components/SiteFooter.vue'
import ThemeToggle from './components/ThemeToggle.vue'
</script>

<template>
  <SiteHeader />
  <main>
    <RouterView />
  </main>
  <!-- 어느 화면에서든 문서 맨 아래에 그대로 온다 -->
  <SiteFooter />
  <!-- 화면 오른쪽 아래에 계속 떠 있다 -->
  <ThemeToggle />
</template>
