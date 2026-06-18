<template>
  <div class="fade-in">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-semibold">媒体资源</h2>
        <p class="text-xs text-dim mt-1">下载记录、目标地址和失败重试</p>
      </div>
      <div class="flex gap-2">
        <select v-model="statusFilter" class="input-base w-36" @change="page = 0; load()">
          <option value="">全部状态</option>
          <option value="queued">排队中</option>
          <option value="running">下载中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
        <button class="btn-ghost" :disabled="loading" @click="load">{{ loading ? '刷新中...' : '刷新' }}</button>
      </div>
    </div>

    <div class="card overflow-x-auto">
      <table v-if="downloads.length">
        <thead>
          <tr>
            <th>状态</th>
            <th>文件</th>
            <th>媒体地址</th>
            <th>来源</th>
            <th>大小</th>
            <th>下载时间</th>
            <th>重试</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in downloads" :key="item.id">
            <td>
              <span class="badge" :class="statusClass(item.status)">{{ statusText(item.status) }}</span>
            </td>
            <td class="min-w-44">
              <div class="text-sm text-white">{{ item.file_name || '—' }}</div>
              <div class="text-[11px] text-dim font-mono">{{ item.mime_type || item.target_type || '—' }}</div>
            </td>
            <td class="min-w-88 max-w-xl">
              <div class="font-mono text-xs truncate" :title="item.target_path || item.local_path || item.source_url">
                {{ item.target_path || item.local_path || '—' }}
              </div>
              <div class="text-[11px] text-dim font-mono truncate mt-1" :title="item.source_url">
                来源: {{ item.source_url || '—' }}
              </div>
              <div v-if="item.error" class="text-[11px] text-err truncate mt-1" :title="item.error">{{ item.error }}</div>
            </td>
            <td class="min-w-40">
              <div class="text-xs">{{ sourceText(item.source_type) }} · {{ triggerText(item.trigger_type) }}</div>
              <div class="text-[11px] text-dim font-mono truncate" :title="item.source_url">
                {{ item.source_chat || '—' }} / {{ item.source_message_id || '—' }}
              </div>
            </td>
            <td class="font-mono text-xs text-dim">{{ fmtBytes(item.file_size) }}</td>
            <td class="min-w-44">
              <div class="text-xs">{{ fmt(item.completed_at || item.started_at || item.created_at) }}</div>
              <div class="text-[11px] text-dim">{{ fmtDuration(item.duration_ms) }}</div>
            </td>
            <td class="font-mono text-xs text-dim">{{ item.retry_count }}</td>
            <td>
              <button class="btn-sm btn-ghost" :disabled="busyId === item.id || item.status === 'running' || item.status === 'queued'" @click="retry(item)">
                {{ busyId === item.id ? '提交中' : '重试' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-center py-10 text-dim text-sm">{{ loading ? '加载中...' : '暂无媒体资源' }}</div>
    </div>

    <div v-if="downloads.length" class="flex justify-center gap-2 mt-5">
      <button class="btn-sm btn-ghost" :disabled="page <= 0" @click="page--; load()">上一页</button>
      <span class="text-dim text-sm leading-8">第 {{ page + 1 }} 页</span>
      <button class="btn-sm btn-ghost" :disabled="downloads.length < pageSize" @click="page++; load()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api.js'

const toast = inject('toast')
const downloads = ref([])
const statusFilter = ref('')
const loading = ref(false)
const busyId = ref(0)
const page = ref(0)
const pageSize = 50
let timer = 0

const statusText = (s) => ({ queued: '排队中', running: '下载中', completed: '已完成', failed: '失败' }[s] || s || '—')
const sourceText = (s) => ({ telegram_media: 'Telegram 媒体', telegram_message_link: '消息链接', http_url: '网页链接' }[s] || s || '—')
const triggerText = (s) => ({ command: '命令', reaction: '表情', web: '控制台' }[s] || s || '—')
const statusClass = (s) => {
  if (s === 'completed') return 'bg-ok/15 text-ok'
  if (s === 'failed') return 'bg-err/15 text-err'
  if (s === 'running' || s === 'queued') return 'bg-warn/15 text-warn'
  return 'bg-bg-input text-dim'
}
const fmt = (s) => s ? new Date(s).toLocaleString('zh-CN') : '—'
const fmtDuration = (ms) => {
  if (!ms) return '耗时 —'
  if (ms < 1000) return `耗时 ${ms} ms`
  return `耗时 ${(ms / 1000).toFixed(1)} s`
}
const fmtBytes = (value) => {
  if (!value) return '—'
  let size = Number(value)
  for (const unit of ['B', 'KB', 'MB', 'GB', 'TB']) {
    if (size < 1024 || unit === 'TB') return unit === 'B' ? `${size} ${unit}` : `${size.toFixed(2)} ${unit}`
    size /= 1024
  }
  return `${size.toFixed(2)} TB`
}

async function load() {
  loading.value = true
  const params = { limit: pageSize, offset: page.value * pageSize }
  if (statusFilter.value) params.status = statusFilter.value
  try {
    downloads.value = await api.getDownloads(params)
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function retry(item) {
  busyId.value = item.id
  try {
    await api.retryDownload(item.id)
    toast('已提交重试')
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busyId.value = 0
  }
}

onMounted(() => {
  load()
  timer = window.setInterval(load, 5000)
})
onUnmounted(() => { if (timer) window.clearInterval(timer) })
</script>
