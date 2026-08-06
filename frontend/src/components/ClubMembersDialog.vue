<script setup>
/* 인원 모달 — 디자인 기획 §5.3 모달3 / api.md §3 GET /clubs/{id}/members
 * 네이티브 <dialog>.showModal() — ESC · 포커스트랩 · 스크롤잠금은 공짜.
 * members 가 빈 배열이면 비로그인·미인증이라 실명을 못 받은 것이다(api.md §3). */
import { ref, computed } from 'vue'
import api from '../api'

const props = defineProps({
  clubId: { type: [String, Number], required: true },
  clubName: { type: String, default: '' },
})

const dlg = ref(null)
const groups = ref([])
const total = ref(0)
const loading = ref(false)
const failed = ref(false)
const loaded = ref(false)

const named = computed(() => groups.value.some((g) => (g.members?.length ?? 0) > 0))
const summary = computed(() => {
  if (loading.value) return '불러오는 중…'
  if (failed.value) return ''
  const ob = groups.value.find((g) => g.gen === null)?.count ?? 0
  const active = total.value - ob
  return `활동중 ${active}명 · OB ${ob}명 · 기수순`
})

async function load() {
  if (loaded.value || loading.value) return
  loading.value = true
  try {
    const r = await api.clubs.members(props.clubId)
    groups.value = r?.groups ?? []
    total.value = r?.total ?? 0
    loaded.value = true
  } catch {
    failed.value = true          // 501 등 — 모달만 빈 상태로
  } finally {
    loading.value = false
  }
}

function open() {
  dlg.value?.showModal()
  load()
}
defineExpose({ open })
</script>

<template>
  <dialog ref="dlg" class="sheet" @click.self="dlg.close()">
    <div class="sheet-hd">
      <h2>{{ clubName }} 부원</h2>
      <p>{{ summary }}</p>
      <button class="x" aria-label="닫기" @click="dlg.close()">✕</button>
    </div>

    <div class="sheet-bd">
      <p v-if="loading" class="sub">불러오는 중…</p>
      <p v-else-if="failed" class="sub">부원 목록은 곧 표시됩니다.</p>
      <p v-else-if="!groups.length" class="sub">아직 등록된 부원이 없습니다.</p>

      <template v-else>
        <p v-if="!named" class="privacy locked">
          <span>🔒</span>
          <span><b>로그인하면 부원 목록을 볼 수 있어요.</b><br>지금은 기수별 인원수만 표시됩니다.</span>
        </p>

        <section v-for="g in groups" :key="g.label" class="gen" :class="{ ob: g.gen === null }">
          <h3>{{ g.label }}<em>{{ g.count }}명<template v-if="g.gen === null"> · 졸업생</template></em></h3>
          <ul v-if="g.members?.length">
            <li v-for="m in g.members" :key="m.id">
              <span v-if="m.role === '동아리장'" class="lead">동아리장</span>
              {{ m.name }}<small>{{ m.dept }}</small>
            </li>
          </ul>
        </section>
      </template>
    </div>
  </dialog>
</template>

<style scoped>
dialog { max-height: min(86vh, 760px); overflow: auto; box-shadow: 0 26px 70px var(--shadowUp); }
dialog::backdrop { backdrop-filter: blur(3px); }

.sheet-hd {
  position: sticky; top: 0; z-index: 2; background: var(--card);
  padding: 22px 24px 14px; border-bottom: 1px solid var(--line);
}
.sheet-hd h2 { margin: 0 0 4px; font-size: 19px; letter-spacing: -.025em; }
.sheet-hd p { margin: 0; font-size: 13px; color: var(--dim); }
.sheet-hd .x {
  position: absolute; top: 16px; right: 16px; width: 32px; height: 32px;
  border: none; border-radius: 9px; background: none; color: var(--dim);
  font: inherit; font-size: 18px; display: grid; place-items: center; cursor: pointer;
}
.sheet-hd .x:hover { background: var(--chip); color: var(--ink); }
.sheet-bd { padding: 20px 24px 24px; }

.privacy.locked { display: flex; gap: 9px; align-items: flex-start; line-height: 1.65; margin: 0 0 18px; }
.privacy.locked b { color: var(--ink); }

.gen { margin-bottom: 22px; }
.gen:last-child { margin-bottom: 0; }
.gen h3 { margin: 0 0 11px; font-size: 14px; display: flex; align-items: center; gap: 9px; letter-spacing: -.01em; }
.gen h3 em { font-style: normal; font-size: 12px; color: var(--dim); font-weight: 400; }
.gen h3::after { content: ""; flex: 1; height: 1px; background: var(--line); }
.gen ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 7px; }
.gen li {
  display: inline-flex; align-items: center; gap: 7px;
  background: var(--bg); border: var(--border); border-radius: var(--r-chip);
  padding: 7px 14px; font-size: 13.5px;
}
.gen li small { color: var(--dim); font-size: 11.5px; }
.gen li .lead {
  background: var(--accent); color: var(--onAccent); border-radius: var(--r-chip);
  padding: 1px 8px; font-size: 10.5px; font-weight: 800;
}
.gen.ob li { opacity: .72; }
</style>
