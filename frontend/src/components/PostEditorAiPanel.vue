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

/* 파일 선택 — 네이티브 <input type=file> 버튼은 브라우저마다 생김새가 달라
 * 폼의 다른 칸과 따로 논다. 입력은 숨기고 우리 버튼으로 연다 (디자인 §6-3). */
const photoInput = ref(null)
const pdfInput = ref(null)

function onPhotos(e) { photoFiles.value = Array.from(e.target.files ?? []) }
function onPdf(e) { pdfFile.value = e.target.files?.[0] ?? null }

function clearPhotos() {
  photoFiles.value = []
  if (photoInput.value) photoInput.value.value = ''
}
function clearPdf() {
  pdfFile.value = null
  if (pdfInput.value) pdfInput.value.value = ''
}

function sizeText(bytes) {
  if (!bytes && bytes !== 0) return ''
  const mb = bytes / (1024 * 1024)
  return mb >= 1 ? `${mb.toFixed(1)}MB` : `${Math.max(1, Math.round(bytes / 1024))}KB`
}

const photoSummary = computed(() => {
  const n = photoFiles.value.length
  if (!n) return ''
  const total = photoFiles.value.reduce((s, f) => s + (f.size ?? 0), 0)
  return `${n}장 · ${sizeText(total)}`
})
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
        <button type="button" class="pick" :class="{ filled: photoFiles.length }" :disabled="pending"
                @click="photoInput?.click()">
          <span class="ico" aria-hidden="true">🖼</span>
          <span class="txt">
            <b>{{ photoFiles.length ? `사진 ${photoFiles.length}장` : '사진 고르기' }}</b>
            <small>{{ photoFiles.length ? photoSummary : 'jpg · png · webp · 여러 장' }}</small>
          </span>
          <span class="cta">{{ photoFiles.length ? '바꾸기' : '찾아보기' }}</span>
        </button>
        <input id="ai-photos" ref="photoInput" class="sr" type="file" accept="image/*" multiple
               :disabled="pending" @change="onPhotos">

        <ul v-if="photoFiles.length" class="picked">
          <li v-for="(f, i) in photoFiles" :key="`${f.name}-${i}`">
            <span class="nm">{{ f.name }}</span>
            <span class="sz">{{ sizeText(f.size) }}</span>
          </li>
        </ul>
        <p v-if="photoFiles.length" class="hint">
          <button type="button" class="lnk" :disabled="pending" @click="clearPhotos">모두 지우기</button>
        </p>
        <p class="hint">메모에 적힌 사실을 구체화하는 데만 씁니다.</p>
      </div>

      <div class="fld">
        <label for="ai-pdf">활동 결과보고서 PDF (선택)</label>
        <button type="button" class="pick" :class="{ filled: !!pdfFile }" :disabled="pending"
                @click="pdfInput?.click()">
          <span class="ico" aria-hidden="true">📄</span>
          <span class="txt">
            <b>{{ pdfFile ? pdfFile.name : 'PDF 고르기' }}</b>
            <small>{{ pdfFile ? sizeText(pdfFile.size) : '결과보고서 한 부' }}</small>
          </span>
          <span class="cta">{{ pdfFile ? '바꾸기' : '찾아보기' }}</span>
        </button>
        <input id="ai-pdf" ref="pdfInput" class="sr" type="file" accept="application/pdf"
               :disabled="pending" @change="onPdf">

        <p v-if="pdfFile" class="hint">
          <button type="button" class="lnk" :disabled="pending" @click="clearPdf">선택 취소</button>
        </p>
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
.fld :disabled { opacity: .55; cursor: not-allowed; }
.hint { margin-top: 5px; }

/* 파일 선택 — 네이티브 버튼 대신 폼의 다른 칸과 같은 높이·테두리를 쓴다 */
.sr {
  position: absolute; width: 1px; height: 1px; padding: 0;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}
.pick {
  width: 100%; display: flex; align-items: center; gap: 11px;
  border: 1.5px dashed var(--line); border-radius: var(--r-input);
  background: var(--bg); color: var(--ink); font: inherit; text-align: left;
  padding: 10px 12px; cursor: pointer;
  transition: border-color var(--t-hover), background var(--t-hover);
}
.pick:hover:not(:disabled) { border-color: var(--accent); background: var(--chip); }
.pick:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.pick.filled { border-style: solid; border-color: var(--accent); background: var(--card); }
.pick .ico { font-size: 17px; line-height: 1; flex: none; }
.pick .txt { min-width: 0; flex: 1; display: block; }
.pick .txt b {
  display: block; font-size: 13.5px; font-weight: 700;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pick .txt small { display: block; margin-top: 2px; font-size: 11.5px; color: var(--dim); }
.pick .cta {
  flex: none; padding: 4px 10px; border-radius: var(--r-chip);
  background: var(--chip); border: 1px solid var(--line);
  font-size: 11.5px; font-weight: 700; color: var(--dim);
}
.pick.filled .cta { background: var(--accent); border-color: transparent; color: var(--onAccent); }

.picked { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.picked li {
  display: flex; gap: 8px; align-items: baseline;
  font-size: 12px; color: var(--dim);
}
.picked .nm { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.picked .sz { flex: none; }

.lnk {
  border: none; background: none; padding: 0; font: inherit; font-size: 12px;
  color: var(--accent); font-weight: 700; text-decoration: underline; cursor: pointer;
}

.ai-act { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
.ai-act .hint { margin-top: 0; }
.keyless .link { color: var(--accent); font-weight: 700; text-decoration: underline; }

.box { margin: 14px 0 0; }

@media (max-width: 720px) {
  .ai-grid { grid-template-columns: 1fr; }
}
</style>
