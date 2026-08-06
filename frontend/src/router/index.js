import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../stores/auth'

/* 화면 목록은 기획서 §8 과 1:1. meta.auth: 로그인 필요 · meta.admin: 관리자 전용 */
const routes = [
  { path: '/', name: 'main', component: () => import('../views/MainView.vue') },
  { path: '/archive', name: 'archive', component: () => import('../views/ArchiveView.vue') },
  { path: '/clubs/:id', name: 'club', component: () => import('../views/ClubDetailView.vue'), props: true },
  { path: '/posts/:id', name: 'post', component: () => import('../views/PostDetailView.vue'), props: true },

  // 로그인·회원가입은 모달이다 (디자인 기획 §6-2). 경로는 남겨두고 모달을 여는 쿼리로 넘긴다 —
  // 라우터 가드와 외부에서 들어온 /login 링크가 그대로 동작해야 하기 때문이다.
  { path: '/login', name: 'login',
    redirect: (to) => ({ path: '/', query: { ...to.query, auth: 'login' } }) },
  { path: '/signup', name: 'signup',
    redirect: (to) => ({ path: '/', query: { ...to.query, auth: 'signup' } }) },
  { path: '/verify', name: 'verify', component: () => import('../views/VerifyView.vue') },

  { path: '/me', name: 'me', component: () => import('../views/MyPageView.vue'), meta: { auth: true } },
  { path: '/clubs/new', name: 'club-apply', component: () => import('../views/ClubApplyView.vue'), meta: { auth: true } },

  { path: '/clubs/:id/manage', name: 'club-manage', component: () => import('../views/ClubManageView.vue'), props: true, meta: { auth: true } },
  { path: '/clubs/:id/posts/new', name: 'post-new', component: () => import('../views/PostEditorView.vue'), props: true, meta: { auth: true } },
  { path: '/posts/:id/edit', name: 'post-edit', component: () => import('../views/PostEditorView.vue'), props: true, meta: { auth: true } },

  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { auth: true, admin: true } },

  { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('../views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved ?? { top: 0 },
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  if (!auth.ready) await auth.load()

  if (to.meta.auth && !auth.isLoggedIn) return { name: 'login', query: { next: to.fullPath } }
  if (to.meta.admin && !auth.isAdmin) return { name: 'main' }
  return true
})

export default router
