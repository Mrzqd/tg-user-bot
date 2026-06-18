<template>
  <div class="fade-in">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold">消息日志</h2>
      <div class="flex gap-2">
        <input class="input-base w-44" v-model="chatFilter" placeholder="按 Chat ID 筛选" @keydown.enter="load" />
        <button class="btn-ghost" @click="load">搜索</button>
        <button class="btn-ghost" @click="chatFilter = ''; load()">重置</button>
      </div>
    </div>
    <div class="card overflow-x-auto">
      <table v-if="logs.length">
        <thead><tr><th>时间</th><th>Chat ID</th><th>话题</th><th>发送者</th><th>消息内容</th><th>消息 ID</th></tr></thead>
        <tbody>
          <tr v-for="l in logs" :key="l.id">
            <td class="text-dim text-xs whitespace-nowrap">{{ fmt(l.created_at) }}</td>
            <td class="font-mono text-xs">{{ l.chat_id }}</td>
            <td class="font-mono text-xs">{{ l.topic_id ? l.topic_id : '—' }}</td>
            <td><span>{{ l.sender_name }}</span><span class="text-dim font-mono text-[11px] ml-1">({{ l.sender_id }})</span></td>
            <td class="max-w-sm truncate">{{ l.text || '(媒体)' }}</td>
            <td class="font-mono text-xs text-dim">{{ l.message_id }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-center py-10 text-dim text-sm">暂无消息日志</div>
    </div>
    <div v-if="logs.length" class="flex justify-center gap-2 mt-5">
      <button class="btn-sm btn-ghost" :disabled="page <= 0" @click="page--; load()">上一页</button>
      <span class="text-dim text-sm leading-8">第 {{ page + 1 }} 页</span>
      <button class="btn-sm btn-ghost" :disabled="logs.length < 50" @click="page++; load()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api.js'
const toast = inject('toast')
const logs = ref([])
const chatFilter = ref('')
const page = ref(0)
const fmt = (s) => s ? new Date(s).toLocaleString('zh-CN') : '—'
async function load() {
  const params = { limit: 50, offset: page.value * 50 }
  if (chatFilter.value) params.chat_id = chatFilter.value
  try { logs.value = await api.getLogs(params) } catch (e) { toast(e.message, 'error') }
}
onMounted(load)
</script>
