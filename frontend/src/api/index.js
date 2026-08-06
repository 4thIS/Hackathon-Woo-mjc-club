/**
 * ★ 모든 API 호출은 여기를 거친다. 컴포넌트에서 fetch 직접 호출 금지.
 *   (frontend/CLAUDE.md 규칙)
 *
 * 계약: docs/api.md
 * 백엔드가 아직 없는 엔드포인트는 이 파일 **안에서만** mock 으로 대체하고
 * `// MOCK` 주석을 남긴다. 연결되면 mock 블록만 지운다.
 */

const BASE = '/api'

/** docs/api.md §0.1 — 모든 에러는 {detail:{code,message}} 한 형태다. */
export class ApiError extends Error {
  constructor(status, code, message) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request(path, { method = 'GET', body, form } = {}) {
  const init = {
    method,
    credentials: 'include',   // 세션 쿠키. 빼면 전부 401이 된다
    headers: {},
  }

  if (form) {
    init.body = form                              // multipart — Content-Type 은 브라우저가 붙인다
  } else if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  }

  const res = await fetch(BASE + path, init)

  if (res.status === 204) return null

  let data = null
  try { data = await res.json() } catch { /* 본문 없음 */ }

  if (!res.ok) {
    const d = data?.detail ?? {}
    throw new ApiError(res.status, d.code ?? 'ERROR', d.message ?? '요청을 처리하지 못했습니다.')
  }
  return data
}

const get = (p) => request(p)
const post = (p, body) => request(p, { method: 'POST', body })
const patch = (p, body) => request(p, { method: 'PATCH', body })
const put = (p, body) => request(p, { method: 'PUT', body })
const del = (p, body) => request(p, { method: 'DELETE', body })   // 탈퇴는 비밀번호를 함께 보낸다

function qs(params) {
  const s = new URLSearchParams(
    Object.entries(params ?? {}).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  ).toString()
  return s ? `?${s}` : ''
}

export const api = {
  health: () => get('/health'),

  // --- 인증·계정 (T1 · docs/api.md §2) ---
  auth: {
    signup: (payload) => post('/auth/signup', payload),
    login: (email, password) => post('/auth/login', { email, password }),
    logout: () => post('/auth/logout'),
    resendVerification: (email) => post('/auth/verify/resend', { email }),
  },
  me: {
    get: () => get('/me'),
    update: (payload) => patch('/me', payload),
    clubs: () => get('/me/clubs'),
    requests: () => get('/me/requests'),
    registerAiKey: (api_key) => post('/me/ai-key', { api_key }),
    deleteAiKey: () => del('/me/ai-key'),
    withdraw: (password) => del('/me', { password }),
  },

  // --- 탐색 (T2 · §3) ---
  clubs: {
    list: (params) => get('/clubs' + qs(params)),
    detail: (id) => get(`/clubs/${id}`),
    posts: (id, { offset = 0, limit = 5 } = {}) => get(`/clubs/${id}/posts` + qs({ offset, limit })),
    members: (id) => get(`/clubs/${id}/members`),
    update: (id, payload) => patch(`/clubs/${id}`, payload),
    transfer: (id, user_id) => post(`/clubs/${id}/transfer`, { user_id }),
    manageMembers: (id) => get(`/clubs/${id}/members/manage`),
    updateMember: (id, userId, payload) => patch(`/clubs/${id}/members/${userId}`, payload),
    removeMember: (id, userId) => del(`/clubs/${id}/members/${userId}`),
  },
  stats: () => get('/stats'),

  // --- 가입·탈퇴 (T3 · §4) ---
  joinForm: {
    get: (clubId) => get(`/clubs/${clubId}/join-form`),
    put: (clubId, payload) => put(`/clubs/${clubId}/join-form`, payload),
  },
  joinRequests: {
    create: (clubId, answers) => post(`/clubs/${clubId}/join-requests`, { answers }),
    listForClub: (clubId) => get(`/clubs/${clubId}/join-requests`),
    approve: (id) => post(`/join-requests/${id}/approve`),
    reject: (id, reason) => post(`/join-requests/${id}/reject`, { reason }),
    cancel: (id) => del(`/join-requests/${id}`),
  },
  leaveRequests: {
    create: (clubId) => post(`/clubs/${clubId}/leave-requests`),
    listForClub: (clubId) => get(`/clubs/${clubId}/leave-requests`),
    approve: (id) => post(`/leave-requests/${id}/approve`),
  },

  // --- 개설·관리자 (T4 · §5) ---
  clubApplications: {
    create: (payload) => post('/club-applications', payload),
    cancel: (id) => del(`/club-applications/${id}`),
  },
  admin: {
    applications: (status) => get('/admin/club-applications' + qs({ status })),
    approve: (id) => post(`/admin/club-applications/${id}/approve`),
    reject: (id, reason) => post(`/admin/club-applications/${id}/reject`, { reason }),
    updateClub: (id, payload) => patch(`/admin/clubs/${id}`, payload),
    users: (params) => get('/admin/users' + qs(params)),
    updateUser: (id, payload) => patch(`/admin/users/${id}`, payload),
    clubs: (params) => get('/admin/clubs' + qs(params)),
  },

  // --- 활동 글 (T5 · §6) ---
  posts: {
    highlights: (limit = 12) => get('/posts/highlights' + qs({ limit })),
    detail: (id) => get(`/posts/${id}`),
    create: (clubId, payload) => post(`/clubs/${clubId}/posts`, payload),
    update: (id, payload) => patch(`/posts/${id}`, payload),
    remove: (id) => del(`/posts/${id}`),
    like: (id) => post(`/posts/${id}/like`),
  },
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/uploads', { method: 'POST', form })
  },

  // --- AI 초안 (T6 · §7) ---
  aiDraft: ({ club_id, memo, photos = [], pdf }) => {
    const form = new FormData()
    form.append('club_id', String(club_id))
    if (memo) form.append('memo', memo)
    photos.forEach((f) => form.append('photos', f))
    if (pdf) form.append('pdf', pdf)
    return request('/ai/draft', { method: 'POST', form })
  },
}

export default api
