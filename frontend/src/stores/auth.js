import { defineStore } from 'pinia'
import api, { ApiError } from '../api'

export const useAuth = defineStore('auth', {
  state: () => ({
    user: null,        // docs/api.md §2 Me 객체
    ready: false,      // /me 1회 조회를 마쳤는지. 라우터 가드가 이걸 기다린다
  }),

  getters: {
    isLoggedIn: (s) => s.user !== null,
    isVerified: (s) => !!s.user?.email_verified,
    isAdmin: (s) => !!s.user?.is_admin,
    hasAiKey: (s) => !!s.user?.ai_key?.registered,
  },

  actions: {
    /** 앱 부팅 시 1회. 401이면 비로그인 — 에러가 아니다. */
    async load() {
      try {
        this.user = await api.me.get()
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) this.user = null
        else throw e
      } finally {
        this.ready = true
      }
    },

    async login(email, password) {
      this.user = await api.auth.login(email, password)
      return this.user
    },

    async logout() {
      await api.auth.logout()
      this.user = null
    },
  },
})
