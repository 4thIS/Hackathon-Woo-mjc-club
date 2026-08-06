<script setup>
/* 약관 원문 — 푸터에서 들어온다. 가입 모달의 요약과 같은 원본(content/terms.js)을 쓴다.
 * 두 문서를 탭으로 갈아 끼운다. 주소의 해시가 곧 탭이라 /terms#privacy 로 바로 들어올 수 있다. */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DOCS, UPDATED_AT } from '../content/terms'

const route = useRoute()
const router = useRouter()

const fromHash = () => {
  const id = route.hash?.slice(1)
  return DOCS.some((d) => d.id === id) ? id : DOCS[0].id
}

const current = ref(fromHash())
const doc = computed(() => DOCS.find((d) => d.id === current.value) ?? DOCS[0])

/* 뒤로가기로 해시가 바뀌어도 탭이 따라온다 */
watch(() => route.hash, () => { current.value = fromHash() })

function select(id) {
  if (current.value === id) return
  current.value = id
  router.replace({ path: route.path, hash: `#${id}` })
}
</script>

<template>
  <div class="wrap container">
    <header class="hd">
      <p class="eyebrow">약관</p>
      <h1 class="page-title">이용약관 · 개인정보 처리방침</h1>
      <p class="sub">최종 개정 {{ UPDATED_AT }}</p>

      <div class="tabs" role="tablist" aria-label="약관 문서">
        <button v-for="d in DOCS" :key="d.id" type="button" role="tab"
                class="tab" :class="{ on: current === d.id }"
                :aria-selected="current === d.id" :aria-controls="`panel-${d.id}`"
                @click="select(d.id)">
          {{ d.title }}
        </button>
      </div>
    </header>

    <article :id="`panel-${doc.id}`" class="doc card" role="tabpanel" :aria-label="doc.title">
      <h2>{{ doc.title }}</h2>
      <p class="lead">{{ doc.lead }}</p>

      <section v-for="s in doc.sections" :key="s.h">
        <h3>{{ s.h }}</h3>
        <p v-for="(line, i) in s.p" :key="i">{{ line }}</p>
      </section>
    </article>
  </div>
</template>

<style scoped>
.wrap { padding: clamp(34px, 6vh, 64px) 0 clamp(60px, 9vh, 110px); max-width: 860px; }

.hd { margin-bottom: 22px; }
.hd .page-title { margin: 0 0 8px; }
.hd .sub { margin: 0; }

/* 탭 — 선택된 쪽만 채워 넣는다 */
.tabs {
  display: flex; gap: 6px; margin-top: 20px;
  padding: 5px; border: var(--border); border-radius: var(--r-chip);
  background: var(--card); width: max-content; max-width: 100%; flex-wrap: wrap;
}
.tab {
  padding: 8px 18px; border: none; border-radius: var(--r-chip);
  background: none; color: var(--dim);
  font: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer;
  transition: background var(--t-hover), color var(--t-hover);
}
.tab:hover { color: var(--ink); }
.tab.on { background: var(--accent); color: var(--onAccent); }

.doc { padding: 26px 28px 30px; margin-top: 18px; }
.doc:hover { box-shadow: 0 5px 16px var(--shadow); transform: none; }
.doc h2 { margin: 0 0 6px; font-size: 21px; font-weight: 700; letter-spacing: -.025em; }
.doc .lead { margin: 0 0 6px; font-size: 13.5px; color: var(--dim); }

.doc section { margin-top: 22px; }
.doc h3 { margin: 0 0 8px; font-size: 15px; font-weight: 700; letter-spacing: -.02em; }
.doc section p {
  margin: 0 0 8px; font-size: 14px; line-height: 1.9; color: var(--dim);
  padding-left: 13px; position: relative;
}
.doc section p::before {
  content: ""; position: absolute; left: 0; top: .78em;
  width: 4px; height: 4px; border-radius: 50%; background: var(--line);
}
</style>
