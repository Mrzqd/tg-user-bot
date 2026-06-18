import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/groups', name: 'groups', component: () => import('./views/Groups.vue') },
  { path: '/rules', name: 'rules', component: () => import('./views/Rules.vue') },
  { path: '/schedules', name: 'schedules', component: () => import('./views/Schedules.vue') },
  { path: '/downloads', name: 'downloads', component: () => import('./views/Downloads.vue') },
  { path: '/logs', name: 'logs', component: () => import('./views/Logs.vue') },
  { path: '/settings', name: 'settings', component: () => import('./views/Settings.vue') },
  { path: '/help', name: 'help', component: () => import('./views/Help.vue') },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
