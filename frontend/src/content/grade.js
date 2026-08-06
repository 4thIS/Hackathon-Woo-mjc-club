/* 학년 표기 — 명지전문대는 2·3년제라 4학년이 없다.
 * 값 4 는 졸업 후 이어 듣는 **전공심화과정**을 뜻한다.
 * 저장 값(1~4)은 그대로 두고 화면 글자만 바꾼다 (api.md §2 grade).
 */

export const GRADE_OPTIONS = [
  { value: 1, label: '1학년' },
  { value: 2, label: '2학년' },
  { value: 3, label: '3학년' },
  { value: 4, label: '전공심화' },
]

/** 목록·프로필에 붙이는 짧은 표기. 값이 없으면 빈 문자열 */
export function gradeLabel(grade) {
  if (!grade) return ''
  return grade === 4 ? '전공심화' : `${grade}학년`
}
