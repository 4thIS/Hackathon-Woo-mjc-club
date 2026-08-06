import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

/* 영문 표제 전용 (.latin). 한글은 기존 폰트 그대로 — Inter 에 한글 글리프가 없어
 * 자동으로 뒤 폰트로 넘어간다. 필요한 두 굵기만 받는다. */
import '@fontsource/inter/400.css'
import '@fontsource/inter/700.css'

import './assets/theme.css'

createApp(App).use(createPinia()).use(router).mount('#app')
