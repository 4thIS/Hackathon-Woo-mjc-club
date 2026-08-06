<script setup>
/* AI 초안 — 레이아웃은 T5(cw), 호출은 T6(wj).
 *
 * 기획: 기획서 §7 (특히 §7.2 환각 방지 · §4.5 개인 키) · api.md §7
 * 디자인: 프론트엔드 디자인 기획 §6 남은 페이지 제작 규칙 (§6-3 폼 · §6-5 warn 박스)
 */
import { ref, computed } from 'vue'
import api from '../api'

const props = defineProps({
  /** 초안 생성 대상 동아리 id */
  clubId: { type: [String, Number], default: null },
  /** useAuth().hasAiKey — false면 버튼 비활성 + 안내 (기획서 §4.5) */
  hasKey: { type: Boolean, default: false },
})

const memo = ref('')
const photoFiles = ref([])
const pdfFile = ref(null)

const pending = ref(false)
const memoRequired = ref('')   // 422 MEMO_REQUIRED 는 토스트가 아니라 이 warn 박스다 (기획서 §7.2)
const error = ref('')
const visionNote = ref('')     // used.vision === false 일 때의 안내 (기획서 §7.4)

const disabled = computed(() => !props.hasKey || pending.value)
const buttonTitle = computed(() =>
  props.hasKey
    ? '메모·사진·PDF로 초안을 만듭니다'
    : '내 정보에서 AI API 키를 등록하면 사용할 수 있어요',
)

const emit = defineEmits(['draft'])

async function generate() {
  if (disabled.value) return
  memoRequired.value = ''
  error.value = ''
  visionNote.value = ''
  pending.value = true
  try {
    const draft = await api.aiDraft({
      club_id: props.clubId,
      memo: memo.value,
      photos: photoFiles.value,
      pdf: pdfFile.value,
    })
    // 편집창에 채워 넣기만 한다. 자동 게시는 없다 (기획서 §7.3)
    emit('draft', draft)
    if (draft.used?.photos && !draft.used?.vision) {
      visionNote.value = '사진은 첨부만 되었습니다. 초안은 메모와 보고서 내용으로 작성했어요.'
    }
  } catch (e) {
    // 메모를 더 달라는 '요청'이지 실패가 아니다 — 붉은 에러로 띄우지 않는다 (기획서 §7.2)
    if (e.code === 'MEMO_REQUIRED') memoRequired.value = e.message
    else error.value = e.message
  } finally {
    pending.value = false
  }
}

function onPhotos(e) { photoFiles.value = Array.from(e.target.files ?? []) }
function onPdf(e) { pdfFile.value = e.target.files?.[0] ?? null }
</script>

<template>
  <section class="ai card" aria-labelledby="ai-hd">
    <div class="ai-hd">
      <p class="eyebrow">AI 초안</p>
      <h2 id="ai-hd">재료를 올리면 제목·본문·태그 초안을 만들어 드려요</h2>
      <p class="hint">
        초안까지만 만듭니다. 자동 게시는 없고, 읽고 고쳐서 올리는 것은 동아리장 본인입니다.
      </p>
    </div>

    <div class="ai-grid">
      <div class="fld memo">
        <label for="ai-memo">메모<span class="req">*</span></label>
        <textarea id="ai-memo" v-model="memo" :disabled="pending"
                  placeholder="10/12 성북동 출사, 12명 참여, 필름 현상은 다음 주"></textarea>
        <p class="hint">
          사실은 메모와 PDF에서만 가져옵니다. 사진만으로는 초안을 만들지 않습니다 (기획서 §7.2).
        </p>
      </div>

      <div class="fld">
        <label for="ai-photos">사진 (선택)</label>
        <input id="ai-photos" type="file" accept="image/*" multiple :disabled="pending" @change="onPhotos">
        <p class="hint">메모에 적힌 사실을 구체화하는 데만 씁니다.</p>
      </div>

      <div class="fld">
        <label for="ai-pdf">활동 결과보고서 PDF (선택)</label>
        <input id="ai-pdf" type="file" accept="application/pdf" :disabled="pending" @change="onPdf">
        <p class="hint">서버가 텍스트를 뽑아 씁니다. 스캔본은 읽지 못합니다.</p>
      </div>
    </div>

    <div class="ai-act">
      <button type="button" class="btn" :disabled="disabled" :title="buttonTitle" @click="generate">
        {{ pending ? '초안을 만드는 중…' : 'AI 초안 생성' }}
      </button>

      <p v-if="!hasKey" class="hint keyless">
        내 정보에서 AI API 키를 등록하면 사용할 수 있어요.
        <RouterLink class="link" to="/me">내 정보로 가기</RouterLink>
      </p>
      <p v-else-if="pending" class="hint">사진이 있으면 10초쯤 걸립니다.</p>
      <p v-else class="hint">초안이 아래 입력란에 채워집니다. 확인하고 고쳐서 올려주세요.</p>
    </div>

    <!-- MEMO_REQUIRED 전용 자리 — 에러가 아니라 요청이다 (기획서 §7.2) -->
    <p v-if="memoRequired" class="warn box">{{ memoRequired }}</p>
    <p v-if="error" class="warn box">{{ error }}</p>
    <p v-if="visionNote" class="privacy box">{{ visionNote }}</p>
  </section>
</template>

<style scoped>
.ai { padding: 20px 22px 22px; }
.ai:hover { box-shadow: 0 5px 16px var(--shadow); transform: none; }

.ai-hd { margin-bottom: 16px; }
.ai-hd .eyebrow { margin: 0 0 4px; }
.ai-hd h2 { margin: 0 0 6px; font-size: 17px; font-weight: 700; letter-spacing: -.025em; }
.ai-hd .hint { margin: 0; }

.ai-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }
.ai-grid .memo { grid-column: 1 / -1; }
.fld textarea { min-height: 74px; resize: vertical; }
.fld input[type="file"] { padding: 8px 10px; font-size: 13px; }
.fld :disabled { opacity: .55; cursor: not-allowed; }
.hint { margin-top: 5px; }

.ai-act { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
.ai-act .hint { margin-top: 0; }
.keyless .link { color: var(--accent); font-weight: 700; text-decoration: underline; }

.box { margin: 14px 0 0; }

@media (max-width: 720px) {
  .ai-grid { grid-template-columns: 1fr; }
}
</style>
