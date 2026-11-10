import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Login',
    component: () => import('@/components/page/Login.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/components/page/Chat.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  if (to.name === 'Chat' && !localStorage.getItem('access_token')) {
    return { name: 'Login' }
  }
  if (to.name === 'Login' && localStorage.getItem('access_token')) {
    return { name: 'Chat' }
  }
  return true
})

export default router
