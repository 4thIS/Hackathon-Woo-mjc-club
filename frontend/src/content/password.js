/* 비밀번호 규칙 — 서버(backend/app/security.py)와 같은 기준을 쓴다.
 * 서버가 최종 판정을 하지만, 화면에서 미리 보여주지 않으면 사용자는 제출하고 나서야 안다.
 */

export const PW_MIN = 8

/** 화면에 체크리스트로 뿌리는 조건들 */
export const PW_RULES = [
  { key: 'len', label: `${PW_MIN}자 이상`, test: (v) => v.length >= PW_MIN },
  { key: 'alpha', label: '영문', test: (v) => /[a-zA-Z]/.test(v) },
  { key: 'digit', label: '숫자', test: (v) => /\d/.test(v) },
  { key: 'special', label: '특수문자', test: (v) => /[^a-zA-Z0-9\s]/.test(v) },
]

/** 모든 조건을 만족하는가 (공백은 허용하지 않는다 — 서버와 같다) */
export function passwordOk(value) {
  const v = value ?? ''
  return !v.includes(' ') && PW_RULES.every((r) => r.test(v))
}
