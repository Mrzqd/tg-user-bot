<template>
  <div class="flex min-h-screen">
    <aside class="w-56 bg-bg-card border-r border-border flex flex-col fixed inset-y-0 left-0 z-100">
      <div class="px-5 py-5 border-b border-border">
        <h1 class="text-base font-semibold text-accent flex items-center gap-2">
          <span class="w-2 h-2 rounded-full inline-block" :class="connected ? 'bg-ok' : 'bg-err'"></span>
          <span>TG Userbot</span>
        </h1>
        <p v-if="statusInfo" class="text-xs text-dim mt-1">{{ statusInfo.first_name }} · @{{ statusInfo.username }}</p>
      </div>
      <nav class="flex-1 p-3 flex flex-col gap-0.5">
        <router-link v-for="item in nav" :key="item.to" :to="item.to"
          class="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-sm text-dim no-underline transition-all duration-150 hover:bg-bg-hover hover:text-white"
          active-class="!bg-accent !text-white"
        >
          <span class="text-base w-5 text-center" v-html="item.icon"></span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="px-4 py-4 border-t border-border">
        <label class="text-[11px] text-dim mb-1.5 block">API 密钥</label>
        <input class="input-base !text-xs !py-1.5" type="password" placeholder="输入 API Key" :value="apiKey" @input="onKeyChange" />
      </div>
    </aside>
    <main class="flex-1 ml-56 p-7 min-h-screen"><slot /></main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getApiKey, setApiKey, api } from '../api.js'

const nav = [
  { to: '/', label: '仪表盘', icon: '&#9632;' },
  { to: '/groups', label: '监控群组', icon: '&#9782;' },
  { to: '/rules', label: '关键词规则', icon: '&#9881;' },
  { to: '/schedules', label: '定时任务', icon: '&#9200;' },
  { to: '/logs', label: '消息日志', icon: '&#9776;' },
  { to: '/settings', label: '系统设置', icon: '&#9881;' },
  { to: '/help', label: '命令帮助', icon: '&#10068;' },
]

const apiKey = ref(getApiKey())
const connected = ref(false)
const statusInfo = ref(null)

function onKeyChange(e) { apiKey.value = e.target.value; setApiKey(e.target.value); fetchStatus() }

async function fetchStatus() {
  try {
    const h = await api.getHealth(); connected.value = h.connected
    if (getApiKey()) statusInfo.value = await api.getStatus()
  } catch { connected.value = false }
}

onMounted(() => { fetchStatus(); setInterval(fetchStatus, 30000) })
</script>
