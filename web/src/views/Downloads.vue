<template>
  <div class="fade-in">
    <PageHeader title="媒体资源" description="下载队列、实时进度与失败重试">
      <select v-model="statusFilter" class="input-base !w-32" @change="page = 0; load()">
        <option value="">全部状态</option>
        <option value="queued">排队中</option>
        <option value="running">下载中</option>
        <option value="completed">已完成</option>
        <option value="failed">失败</option>
      </select>
      <button class="btn-ghost" :disabled="loading" @click="load()">
        <Icon name="refresh" :size="14" :class="loading ? 'animate-spin' : ''" />
        刷新
      </button>
    </PageHeader>

    <!-- 概览：队列与实时速度 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
      <button
        v-for="card in statCards"
        :key="card.status"
        type="button"
        class="card !p-4 flex items-center gap-3 text-left cursor-pointer transition-all duration-150 hover:border-border-strong"
        :class="statusFilter === card.status ? '!border-accent/60 ring-1 ring-accent/25' : ''"
        @click="toggleFilter(card.status)"
      >
        <div class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" :class="card.tint">
          <Icon :name="card.icon" :size="17" />
        </div>
        <div class="min-w-0">
          <div class="text-xl font-bold leading-tight tabular-nums">{{ stats[card.status] }}</div>
          <div class="text-[11px] text-dim truncate">
            {{ card.label }}<template v-if="card.status === 'running' && stats.total_speed_bps"> · {{ fmtSpeed(stats.total_speed_bps) }}</template>
          </div>
        </div>
      </button>
    </div>

    <div class="card-table">
      <div v-if="!loaded" class="py-16 flex justify-center">
        <Icon name="loader" :size="20" class="animate-spin text-faint" />
      </div>
      <div v-else-if="downloads.length" class="overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>文件</th>
              <th class="min-w-48">状态 / 进度</th>
              <th>保存位置</th>
              <th>来源</th>
              <th>时间</th>
              <th class="!text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in downloads" :key="item.id">
              <td class="min-w-44">
                <div class="font-medium max-w-52 truncate" :title="item.file_name">{{ item.file_name || '—' }}</div>
                <div class="text-[11px] text-faint font-mono mt-0.5">
                  {{ item.mime_type || item.target_type || '—' }} · {{ fmtBytes(item.file_size || item.total_bytes) }}
                </div>
              </td>
              <td>
                <!-- 下载/上传中：进度条 + 速度 -->
                <template v-if="item.status === 'running'">
                  <div class="flex items-center justify-between gap-3 mb-1.5">
                    <span class="text-xs font-medium text-warn whitespace-nowrap">
                      {{ item.stage === 'uploading' ? '上传中' : '下载中' }}<template v-if="pct(item) !== null"> {{ pct(item) }}%</template>
                    </span>
                    <span class="text-[11px] text-faint font-mono whitespace-nowrap">{{ fmtSpeed(item.speed_bps) || '— /s' }}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-bg-input overflow-hidden w-44">
                    <div
                      v-if="pct(item) !== null"
                      class="h-full rounded-full transition-all duration-700"
                      :class="item.stage === 'uploading' ? 'bg-accent' : 'bg-warn'"
                      :style="{ width: pct(item) + '%' }"
                    ></div>
                    <div v-else class="h-full w-full bg-warn/35 animate-pulse"></div>
                  </div>
                  <div class="text-[11px] text-faint mt-1 font-mono whitespace-nowrap">
                    {{ fmtBytes(item.downloaded_bytes) || '0 B' }}<template v-if="item.total_bytes"> / {{ fmtBytes(item.total_bytes) }}</template>
                  </div>
                </template>
                <!-- 其它状态：徽章 -->
                <template v-else>
                  <span :class="statusClass(item.status)">
                    <span v-if="item.status === 'queued'" class="w-1.5 h-1.5 rounded-full bg-current animate-pulse"></span>
                    {{ statusText(item.status) }}
                  </span>
                  <div v-if="item.retry_count" class="text-[11px] text-faint mt-1">已重试 {{ item.retry_count }} 次</div>
                  <div v-if="item.error" class="text-[11px] text-err max-w-52 truncate mt-1" :title="item.error">{{ item.error }}</div>
                </template>
              </td>
              <td class="min-w-60 max-w-80">
                <div class="font-mono text-xs truncate" :title="item.target_path || item.local_path || ''">
                  {{ item.target_path || item.local_path || '—' }}
                </div>
                <div v-if="item.source_url" class="text-[11px] text-faint font-mono truncate mt-1" :title="item.source_url">
                  来源：{{ item.source_url }}
                </div>
              </td>
              <td class="min-w-36">
                <div class="text-xs">{{ sourceText(item.source_type) }} · {{ triggerText(item.trigger_type) }}</div>
                <div class="text-[11px] text-faint font-mono truncate mt-0.5">
                  {{ item.source_chat || '—' }} / {{ item.source_message_id || '—' }}
                </div>
              </td>
              <td class="whitespace-nowrap">
                <div class="text-xs">{{ fmtDate(item.completed_at || item.started_at || item.created_at) }}</div>
                <div v-if="item.duration_ms" class="text-[11px] text-faint mt-0.5">耗时 {{ fmtDuration(item.duration_ms) }}</div>
              </td>
              <td>
                <div class="flex justify-end">
                  <button
                    class="btn-ghost !h-7 !px-2.5 !text-xs"
                    :disabled="busyId === item.id || item.status === 'running' || item.status === 'queued'"
                    @click="retry(item)"
                  >
                    <Icon name="retry" :size="12" :class="busyId === item.id ? 'animate-spin' : ''" />
                    {{ busyId === item.id ? '提交中' : '重试' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="download" title="暂无媒体资源" hint="通过命令、点赞或控制台触发下载后，记录会显示在这里" />
    </div>

    <TablePagination
      v-if="loaded && (page > 0 || downloads.length)"
      :page="page"
      :has-more="downloads.length >= pageSize"
      @change="p => { page = p; load() }"
    />
  </div>
</template>

<script setup>
import { inject, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api.js'
import { fmtDate, fmtBytes, fmtDuration, fmtSpeed } from '../format.js'
import Icon from '../components/Icon.vue'
import PageHeader from '../components/PageHeader.vue'
import EmptyState from '../components/EmptyState.vue'
import TablePagination from '../components/TablePagination.vue'

const toast = inject('toast')
const downloads = ref([])
const stats = ref({ queued: 0, running: 0, completed: 0, failed: 0, total_speed_bps: 0 })
const statusFilter = ref('')
const loaded = ref(false)
const loading = ref(false)
const busyId = ref(0)
const page = ref(0)
const pageSize = 50
let timer = 0

const statCards = [
  { status: 'running', label: '下载中', icon: 'download', tint: 'bg-warn/12 text-warn' },
  { status: 'queued', label: '排队中', icon: 'clock', tint: 'bg-accent/12 text-accent' },
  { status: 'completed', label: '已完成', icon: 'check-circle', tint: 'bg-ok/12 text-ok' },
  { status: 'failed', label: '失败', icon: 'alert-circle', tint: 'bg-err/12 text-err' },
]

const statusText = (s) => ({ queued: '排队中', running: '下载中', completed: '已完成', failed: '失败' }[s] || s || '—')
const sourceText = (s) => ({ telegram_media: 'Telegram 媒体', telegram_message_link: '消息链接', http_url: '网页链接' }[s] || s || '—')
const triggerText = (s) => ({ command: '命令', reaction: '表情', web: '控制台' }[s] || s || '—')
const statusClass = (s) => {
  if (s === 'completed') return 'badge-ok'
  if (s === 'failed') return 'badge-err'
  if (s === 'running' || s === 'queued') return 'badge-warn'
  return 'badge-dim'
}

const pct = (item) => {
  if (!item.total_bytes) return null
  return Math.min(Math.round((item.downloaded_bytes / item.total_bytes) * 100), 100)
}

function toggleFilter(status) {
  statusFilter.value = statusFilter.value === status ? '' : status
  page.value = 0
  load()
}

// background = 定时静默刷新：不显示 loading、失败不弹错误，避免界面闪烁和错误刷屏
async function load(background = false) {
  if (!background) loading.value = true
  const params = { limit: pageSize, offset: page.value * pageSize }
  if (statusFilter.value) params.status = statusFilter.value
  try {
    const [list, stat] = await Promise.all([api.getDownloads(params), api.getDownloadStats()])
    downloads.value = list
    stats.value = stat
  } catch (e) {
    if (!background) toast(e.message, 'error')
  } finally {
    loading.value = false
    loaded.value = true
  }
}

// 有活跃任务时 2s 刷新进度，空闲时降到 6s
function scheduleNext() {
  const active = (stats.value.running + stats.value.queued) > 0
  timer = window.setTimeout(async () => {
    if (!document.hidden) await load(true)
    scheduleNext()
  }, active ? 2000 : 6000)
}

async function retry(item) {
  busyId.value = item.id
  try {
    await api.retryDownload(item.id)
    toast('已提交重试')
    await load(true)
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    busyId.value = 0
  }
}

onMounted(async () => {
  await load()
  scheduleNext()
})
onUnmounted(() => window.clearTimeout(timer))
</script>
