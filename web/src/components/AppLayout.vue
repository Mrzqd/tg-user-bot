<template>
  <div class="min-h-screen">
    <!-- 移动端顶栏 -->
    <header class="lg:hidden fixed top-0 inset-x-0 z-90 h-13 flex items-center gap-2 px-3 bg-bg-card/90 backdrop-blur border-b border-border">
      <button class="btn-icon" title="打开菜单" @click="sidebarOpen = true">
        <Icon name="menu" :size="18" />
      </button>
      <div class="flex items-center gap-2">
        <div class="w-6 h-6 rounded-lg bg-gradient-to-br from-accent to-violet flex items-center justify-center text-white">
          <Icon name="send" :size="12" />
        </div>
        <span class="text-sm font-semibold">TG Userbot</span>
      </div>
    </header>

    <!-- 移动端遮罩 -->
    <div
      v-if="sidebarOpen"
      class="lg:hidden fixed inset-0 z-95 bg-black/55 backdrop-blur-sm"
      @click="sidebarOpen = false"
    ></div>

    <!-- 侧边栏 -->
    <aside
      class="fixed inset-y-0 left-0 z-100 w-60 bg-bg-card border-r border-border flex flex-col transition-transform duration-250 -translate-x-full lg:translate-x-0"
      :class="sidebarOpen ? '!translate-x-0 shadow-2xl shadow-black/50' : ''"
    >
      <div class="flex items-center gap-3 px-5 h-16 border-b border-border shrink-0">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-accent to-violet flex items-center justify-center text-white shadow-lg shadow-accent/25">
          <Icon name="send" :size="16" />
        </div>
        <div class="leading-tight min-w-0">
          <div class="text-[15px] font-bold tracking-tight">TG Userbot</div>
          <div class="text-[11px] text-faint">Web 控制台</div>
        </div>
      </div>

      <nav class="flex-1 overflow-y-auto p-3 flex flex-col gap-1">
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 h-9.5 rounded-lg text-[13px] font-medium no-underline transition-colors duration-150"
          :class="route.path === item.to
            ? 'bg-accent/12 text-accent-light'
            : 'text-dim hover:bg-bg-hover hover:text-white'"
        >
          <Icon :name="item.icon" :size="16" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="p-3 border-t border-border shrink-0">
        <div class="flex items-center gap-2.5 px-2.5 py-2 rounded-xl bg-bg-sunken border border-border/70">
          <span class="w-2 h-2 rounded-full shrink-0" :class="connected ? 'bg-ok' : 'bg-err'"></span>
          <div class="flex-1 min-w-0 leading-tight">
            <div class="text-xs font-medium truncate">
              {{ statusInfo?.telegram_authorized ? (statusInfo.first_name || 'Telegram') : 'Telegram 未登录' }}
            </div>
            <div class="text-[11px] text-faint truncate">
              {{ statusInfo?.telegram_authorized
                ? '@' + (statusInfo.username || '—')
                : (connected ? '服务已连接' : '服务未连接') }}
            </div>
          </div>
          <button class="btn-icon !w-7 !h-7" title="退出登录" @click="logout">
            <Icon name="log-out" :size="14" />
          </button>
        </div>
      </div>
    </aside>

    <!-- 主内容 -->
    <main class="lg:pl-60 pt-13 lg:pt-0 min-h-screen">
      <div class="p-4 sm:p-6 lg:p-8 max-w-350 mx-auto">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api, setAccessToken } from '../api.js'
import Icon from './Icon.vue'

const nav = [
  { to: '/', label: '仪表盘', icon: 'dashboard' },
  { to: '/groups', label: '监控群组', icon: 'users' },
  { to: '/rules', label: '关键词规则', icon: 'zap' },
  { to: '/schedules', label: '定时任务', icon: 'clock' },
  { to: '/downloads', label: '媒体资源', icon: 'download' },
  { to: '/logs', label: '消息日志', icon: 'file-text' },
  { to: '/settings', label: '系统设置', icon: 'settings' },
  { to: '/help', label: '命令帮助', icon: 'help' },
]

const route = useRoute()
const connected = ref(false)
const statusInfo = ref(null)
const sidebarOpen = ref(false)
let timer = 0

watch(() => route.path, () => { sidebarOpen.value = false })

function logout() {
  setAccessToken('')
  location.reload()
}

async function fetchStatus() {
  try {
    const h = await api.getHealth()
    connected.value = Boolean(h.connected)
    statusInfo.value = await api.getStatus()
  } catch {
    connected.value = false
  }
}

onMounted(() => {
  fetchStatus()
  timer = window.setInterval(fetchStatus, 30000)
})
onUnmounted(() => window.clearInterval(timer))
</script>
