<script setup>
/* 성향 설문 → 동아리 추천 TOP 3 — 명세: docs/api.md §7
 *
 * 답은 화면 상태로만 들고 있다가 닫으면 사라진다. 서버도 결과를 저장하지 않는다.
 */
import { computed, reactive, ref, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../api'

/* 6문항 양자택일. 서버의 AXES 와 순서·의미가 같아야 한다 (ai_recommend.py) */
const QUESTIONS = [
  { q: '동아리에서 보내고 싶은 시간은?',
    a: '몸을 움직이며 함께 뛰는 시간', b: '앉아서 만들고 다듬는 시간' },
  { q: '어떤 사이가 편한가요?',
    a: '여러 사람과 넓게 어울리기', b: '소수와 깊게 친해지기' },
  { q: '활동에 바라는 것은?',
    a: '대회·성과처럼 뚜렷한 목표', b: '부담 없는 취미와 휴식' },
  { q: '일정은 어떤 쪽이 좋나요?',
    a: '정해진 요일에 규칙적으로', b: '그때그때 유연하게' },
  { q: '더 끌리는 쪽은?',
    a: '남을 돕고 사회에 보탬이 되는 일', b: '내 실력을 키우는 일' },
  { q: '결과는 어떻게 남기고 싶나요?',
    a: '무대·전시로 보여주기', b: '과정 자체를 즐기기' },
]

const props = defineProps({
  hasKey: { type: Boolean, default: false },
})

const dlg = ref(null)
const step = ref(0)               // 0..QUESTIONS.length-1
const picks = reactive([])        // 'A' | 'B'
const pending = ref(false)
const error = ref('')
const result = ref(null)          // { items, traits }

const progress = computed(() => Math.round((picks.length / QUESTIONS.length) * 100))
const current = computed(() => QUESTIONS[step.value])

/* 생성 중 표시 — AI 초안 패널과 같은 방식(단계 + 경과 초) */
const STEPS = ['설문 결과를 읽는 중', '동아리 활동 기록을 살피는 중', '어울리는 곳을 고르는 중', '거의 다 됐어요']
const elapsed = ref(0)
let timer = null
const stepText = computed(() => STEPS[Math.min(Math.floor(elapsed.value / 4), STEPS.length - 1)])

function reset() {
  step.value = 0
  picks.splice(0)
  error.value = ''
  result.value = null
  pending.value = false
}

function open() {
  reset()
  if (!dlg.value?.open) dlg.value?.showModal()
}
defineExpose({ open })

function close() {
  dlg.value?.close()
}

function back() {
  if (pending.value || step.value === 0) return
  step.value -= 1
  picks.splice(step.value)
}

async function pick(choice) {
  picks[step.value] = choice
  if (step.value < QUESTIONS.length - 1) {
    step.value += 1
    return
  }
  await submit()
}

async function submit() {
  error.value = ''
  pending.value = true
  elapsed.value = 0
  clearInterval(timer)
  timer = setInterval(() => { elapsed.value += 1 }, 1000)
  try {
    result.value = await api.aiRecommend(picks.join(''))
  } catch (e) {
    error.value = e.message
  } finally {
    pending.value = false
    clearInterval(timer)
  }
}

function again() {
  reset()
}

onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <dialog ref="dlg" @click.self="close()">
    <div class="sheet-hd">
      <h2>내 성향 분석</h2>
      <p>여섯 가지만 고르면 어울리는 동아리를 찾아드립니다.</p>
      <button class="x" aria-label="닫기" @click="close()">✕</button>
    </div>

    <!-- 키 없음 -->
    <template v-if="!hasKey">
      <div class="sheet-bd">
        <p class="msg">
          이 기능은 <b>본인의 AI API 키</b>로 동작합니다. 내 정보에서 키를 등록하면 사용할 수 있어요.
        </p>
        <p class="privacy">설문 답과 추천 결과는 어디에도 저장하지 않습니다.</p>
      </div>
      <div class="sheet-ft">
        <button class="btn ghost" @click="close()">닫기</button>
        <RouterLink class="btn" to="/me" @click="close()">내 정보로 가기</RouterLink>
      </div>
    </template>

    <!-- 분석 중 -->
    <template v-else-if="pending">
      <div class="sheet-bd busy">
        <span class="orb"><i></i><i></i><i></i></span>
        <p class="busy-t">AI가 동아리를 고르는 중</p>
        <p class="busy-s">{{ stepText }} · {{ elapsed }}초</p>
      </div>
    </template>

    <!-- 결과 -->
    <template v-else-if="result">
      <div class="sheet-bd">
        <ul class="traits">
          <li v-for="t in result.traits" :key="t">{{ t }}</li>
        </ul>

        <ol class="picks">
          <li v-for="(it, i) in result.items" :key="it.club_id">
            <div class="rank">{{ i + 1 }}</div>
            <div class="body">
              <p class="nm">
                <RouterLink :to="`/clubs/${it.club_id}`" @click="close()">{{ it.name }}</RouterLink>
                <span class="tag">{{ it.category }}</span>
                <span class="tag" :class="{ open: it.recruit_status !== '모집마감' }">
                  {{ it.recruit_status }}
                </span>
              </p>
              <p class="why">{{ it.reason }}</p>
            </div>
          </li>
        </ol>

        <p class="privacy">이 결과는 저장하지 않습니다. 창을 닫으면 사라집니다.</p>
      </div>
      <div class="sheet-ft">
        <button class="btn ghost" @click="again">다시 하기</button>
        <button class="btn" @click="close()">확인</button>
      </div>
    </template>

    <!-- 설문 -->
    <template v-else>
      <div class="sheet-bd">
        <div class="bar" :style="{ '--p': `${progress}%` }" aria-hidden="true"><i></i></div>
        <p class="count">{{ step + 1 }} / {{ QUESTIONS.length }}</p>

        <h3 class="q">{{ current.q }}</h3>
        <div class="opts">
          <button type="button" class="opt" @click="pick('A')">{{ current.a }}</button>
          <button type="button" class="opt" @click="pick('B')">{{ current.b }}</button>
        </div>

        <p v-if="error" class="warn">{{ error }}</p>
        <p class="privacy">답은 저장하지 않습니다. 추천을 만드는 데만 씁니다.</p>
      </div>
      <div class="sheet-ft">
        <button class="btn ghost" :disabled="step === 0" @click="back">이전</button>
        <button class="btn ghost" @click="close()">그만두기</button>
      </div>
    </template>
  </dialog>
</template>

<style scoped>
.sheet-hd {
  position: relative;
  padding: 22px 52px 16px 24px;
  border-bottom: 1px solid var(--line);
}
.sheet-hd h2 { margin: 0; font-size: 19px; font-weight: 700; letter-spacing: -.025em; }
.sheet-hd p { margin: 6px 0 0; font-size: 13px; color: var(--dim); }
.sheet-hd .x {
  position: absolute; right: 14px; top: 16px;
  width: 32px; height: 32px; border-radius: 9px;
  border: none; background: none; color: var(--dim);
  font: inherit; font-size: 15px; cursor: pointer;
}
.sheet-hd .x:hover { background: var(--chip); color: var(--ink); }

.sheet-bd { padding: 20px 24px; }
.sheet-bd .msg { margin: 0 0 14px; font-size: 14px; line-height: 1.85; }

.sheet-ft {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 16px 24px 20px; border-top: 1px solid var(--line);
}

/* --- 설문 --- */
.bar { height: 4px; border-radius: 999px; background: var(--chip); overflow: hidden; }
.bar i { display: block; height: 100%; width: var(--p); background: var(--accent); transition: width .3s ease; }
.count { margin: 9px 0 0; font-size: 12px; color: var(--dim); font-variant-numeric: tabular-nums; }

.q { margin: 12px 0 16px; font-size: 17px; font-weight: 700; letter-spacing: -.025em; line-height: 1.5; }

.opts { display: flex; flex-direction: column; gap: 9px; }
.opt {
  width: 100%; text-align: left;
  padding: 15px 16px;
  border: var(--border); border-radius: var(--r-input);
  background: var(--card); color: var(--ink);
  font: inherit; font-size: 14.5px; line-height: 1.5; cursor: pointer;
  transition: border-color var(--t-hover), background var(--t-hover), transform var(--t-hover);
}
.opt:hover { border-color: var(--accent); background: var(--chip); transform: translateY(-1px); }

.privacy { margin-top: 14px; }
.warn { margin-top: 14px; }

/* --- 분석 중 --- */
.busy { text-align: center; padding: 46px 24px 50px; }
.busy-t { margin: 14px 0 0; font-size: 15px; font-weight: 700; letter-spacing: -.02em; }
.busy-s { margin: 5px 0 0; font-size: 12.5px; color: var(--dim); font-variant-numeric: tabular-nums; }
.orb { display: inline-flex; gap: 7px; }
.orb i {
  width: 9px; height: 9px; border-radius: 50%; background: var(--accent);
  animation: breathe 1.25s ease-in-out infinite;
}
.orb i:nth-child(2) { animation-delay: .16s; }
.orb i:nth-child(3) { animation-delay: .32s; }
@keyframes breathe {
  0%, 100% { transform: scale(.65); opacity: .35; }
  45% { transform: scale(1.15); opacity: 1; }
}

/* --- 결과 --- */
.traits {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin: 0 0 16px; padding: 0; list-style: none;
}
.traits li {
  background: var(--chip); border-radius: var(--r-chip);
  padding: 4px 11px; font-size: 11.5px; color: var(--dim); font-weight: 600;
}

.picks { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 12px; }
.picks li { display: flex; gap: 13px; align-items: flex-start; }
.rank {
  flex: none; width: 26px; height: 26px; border-radius: 50%;
  display: grid; place-items: center;
  background: var(--accent); color: var(--onAccent);
  font-size: 13px; font-weight: 800;
}
.picks .body { min-width: 0; }
.nm { margin: 0 0 5px; display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.nm a { font-size: 15.5px; font-weight: 700; letter-spacing: -.02em; }
.nm a:hover { color: var(--accent); text-decoration: underline; }
.tag {
  background: var(--chip); border: 1px solid var(--line); border-radius: var(--r-chip);
  padding: 2px 9px; font-size: 11px; color: var(--dim); font-weight: 600;
}
.tag.open { color: var(--accent); border-color: var(--accent); }
.why { margin: 0; font-size: 13.5px; line-height: 1.8; color: var(--dim); }

@media (prefers-reduced-motion: reduce) {
  .orb i { animation: none; }
  .opt:hover { transform: none; }
}
</style>
