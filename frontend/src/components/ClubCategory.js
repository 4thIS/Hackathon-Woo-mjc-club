/* 분야 → theme.css 카테고리 토큰·대체 이모지 매핑 (디자인 기획 §2)
 * 사진이 없는 자리는 분야 그라데이션 + 이모지로 채운다. */

export const CATEGORIES = {
  '학술·전공': { key: 'academic', emoji: '💻' },
  '공연·예술': { key: 'art', emoji: '🎭' },
  '체육': { key: 'sports', emoji: '🏃' },
  '봉사': { key: 'volunteer', emoji: '🤝' },
  '취미·교양': { key: 'hobby', emoji: '🎲' },
}

export const catKey = (c) => CATEGORIES[c]?.key ?? 'academic'
export const catEmoji = (c) => CATEGORIES[c]?.emoji ?? '🎈'

/** 인라인 style 로 넘길 그라데이션 변수 — hex 하드코딩 없이 토큰만 참조한다 */
export function catVars(c) {
  const k = catKey(c)
  return { '--ph-a': `var(--cat-${k}-a)`, '--ph-b': `var(--cat-${k}-b)` }
}

/* 활동 글 대체 이모지 — 글 id 로 고정 선택(새로고침해도 안 바뀐다) */
const POST_EMOJI = ['🌱', '🧰', '📝', '🎬', '📚', '🏫', '🐛', '🎄', '🔀', '🏆', '🚀', '☁️', '🎤', '🤝', '📊', '🗺️', '🔍', '🧑‍💻']
export const postEmoji = (id) => POST_EMOJI[Math.abs(Number(id) || 0) % POST_EMOJI.length]
