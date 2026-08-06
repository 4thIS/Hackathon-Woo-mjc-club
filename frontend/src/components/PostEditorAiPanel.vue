<script setup>
/* AI 초안 자리 — T5(cw)가 레이아웃만 만들어 둔 껍데기다.
 *
 * ★ 지금은 아무것도 호출하지 않는다. api.aiDraft 는 T6(wj)이 여기에 꽂는다.
 *   (구현계획 T5: "작성 화면에 'AI 초안' 버튼 자리를 비워둔다")
 *
 * 기획: 기획서 §7 (특히 §7.2 환각 방지 · §4.5 개인 키) · api.md §7
 * 디자인: 프론트엔드 디자인 기획 §6 남은 페이지 제작 규칙 (§6-3 폼 · §6-5 warn 박스)
 */
import { ref, computed } from 'vue'

const props = defineProps({
  /** 초안 생성 대상 동아리 id — T6이 api.aiDraft({ club_id }) 에 그대로 넣는다 */
  clubId: { type: [String, Number], default: null },
  /** useAuth().hasAiKey — false면 버튼 비활성 + 안내 (기획서 §4.5) */
  hasKey: { type: Boolean, default: false },
})

/* T6이 채워 쓸 재료들. 지금은 화면에 무엇이 들어가는지 보여주기 위한 disabled 상태다. */
const memo = ref('')
const photoFiles = ref([])
const pdfFile = ref(null)

/* T6이 지우고 실제 로딩/에러 상태로 대체할 자리 */
const pending = ref(false)
const memoRequired = ref('')   // 422 MEMO_REQUIRED 는 토스트가 아니라 이 warn 박스다 (기획서 §7.2)
const error = ref('')
const visionNote = ref('')     // used.vision === false 일 때의 안내 (기획서 §7.4)

/* T5 단계에서는 키가 있어도 동작하지 않는다. T6이 이 상수를 지운다. */
const NOT_WIRED_YET = true

const disabled = computed(() => NOT_WIRED_YET || !props.hasKey || pending.value)
const buttonTitle = computed(() =>
  NOT_WIRED_YET
    ? 'T6에서 연결 예정입니다 — 지금은 동작하지 않습니다.'
    : (props.hasKey ? '메모·사진·PDF로 초안을 만듭니다' : '내 정보에서 AI API 키를 등록하면 사용할 수 있어요'),
)

/*
  TODO(T6/wj): api.aiDraft({ club_id: props.clubId, memo, photos: photoFiles, pdf: pdfFile }) 호출 →
       응답 {title, body, tags} 를 각 입력에 채운다.  (emit('draft', { title, body, tags }) 하면
       PostEditorView 가 폼에 반영한다 — 핸들러는 이미 붙어 있다)
       422 MEMO_REQUIRED 는 에러 토스트가 아니라 .warn 박스로 렌더할 것 (기획서 §7.2)
       그 밖의 code(PDF_UNREADABLE · AI_KEY_NOT_REGISTERED · AI_GATEWAY_ERROR · AI_QUOTA_EXCEEDED)는
       ApiError 의 e.message 를 그대로 노출한다 (api.md §0.1).
       used.vision === false 면 "사진은 첨부만 되었습니다" 안내를 띄운다 (기획서 §7.4).
       다시 생성 버튼은 두지 않는다 (기획서 §7.3).
*/
defineEmits(['draft'])

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
        <textarea id="ai-memo" v-model="memo" disabled
                  placeholder="10/12 성북동 출사, 12명 참여, 필름 현상은 다음 주"></textarea>
        <p class="hint">
          사실은 메모와 PDF에서만 가져옵니다. 사진만으로는 초안을 만들지 않습니다 (기획서 §7.2).
        </p>
      </div>

      <div class="fld">
        <label for="ai-photos">사진 (선택)</label>
        <input id="ai-photos" type="file" accept="image/*" multiple disabled @change="onPhotos">
        <p class="hint">메모에 적힌 사실을 구체화하는 데만 씁니다.</p>
      </div>

      <div class="fld">
        <label for="ai-pdf">활동 결과보고서 PDF (선택)</label>
        <input id="ai-pdf" type="file" accept="application/pdf" disabled @change="onPdf">
        <p class="hint">서버가 텍스트를 뽑아 씁니다. 스캔본은 읽지 못합니다.</p>
      </div>
    </div>

    <!-- TODO(T6/wj): api.aiDraft({club_id, memo, photos, pdf}) 호출 →
         응답 {title, body, tags} 를 각 입력에 채운다.
         422 MEMO_REQUIRED 는 에러 토스트가 아니라 .warn 박스로 렌더할 것 (기획서 §7.2) -->
    <div class="ai-act">
      <button type="button" class="btn" :disabled="disabled" :title="buttonTitle">
        {{ pending ? '초안을 만드는 중…' : 'AI 초안 생성' }}
      </button>

      <p v-if="!hasKey" class="hint keyless">
        내 정보에서 AI API 키를 등록하면 사용할 수 있어요.
        <RouterLink class="link" to="/me">내 정보로 가기</RouterLink>
      </p>
      <p v-else class="hint">이 버튼은 T6에서 연결됩니다. 지금은 아래 입력란에 직접 적어 주세요.</p>
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
