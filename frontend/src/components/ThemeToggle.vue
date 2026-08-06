<script setup>
/* 테마 전환 — 화면 오른쪽 아래에 계속 떠 있는다.
 * 헤더에 두면 아래로 스크롤한 뒤에는 보이지 않는다. 어느 화면 어느 위치에서든
 * 바로 바꿀 수 있어야 라이트·다크를 견줘 보기 편하다.
 */
import { onMounted, ref } from 'vue'

const theme = ref('light')

onMounted(() => {
  const saved = localStorage.getItem('theme')
  theme.value = saved ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  apply()
})

function apply() {
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('theme', theme.value)
}

function toggle() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  apply()
}
</script>

<template>
  <button
    class="theme-fab"
    type="button"
    :aria-label="theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'"
    :title="theme === 'dark' ? '라이트 모드로' : '다크 모드로'"
    @click="toggle"
  >
    <span aria-hidden="true">◐</span>
  </button>
</template>

<style scoped>
.theme-fab {
  position: fixed;
  right: clamp(16px, 2.5vw, 28px);
  bottom: clamp(16px, 2.5vw, 28px);
  z-index: 60;                       /* 헤더(50)보다 위. 모달은 top layer 라 늘 이보다 위다 */

  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: var(--border);
  background: var(--card);
  color: var(--ink);
  font-size: 19px;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 6px 20px var(--shadow);
  transition: border-color var(--t-hover), color var(--t-hover), transform var(--t-hover);
}
.theme-fab:hover {
  border-color: var(--accent);
  color: var(--accent);
  transform: translateY(-2px);
}
.theme-fab:active { transform: none; }

@media (prefers-reduced-motion: reduce) {
  .theme-fab:hover { transform: none; }
}
</style>
