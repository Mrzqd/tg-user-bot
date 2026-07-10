<template>
  <div class="fade-in">
    <PageHeader title="消息日志" description="监控群组内捕获的消息记录">
      <div class="relative">
        <Icon name="search" :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-faint pointer-events-none" />
        <input
          v-model="chatFilter"
          class="input-base !w-52 !pl-8.5"
          placeholder="按 Chat ID 筛选"
          @keydown.enter="search"
        />
      </div>
      <button class="btn-ghost" @click="search">搜索</button>
      <button v-if="chatFilter" class="btn-ghost" @click="reset">重置</button>
    </PageHeader>

    <div class="card-table">
      <div v-if="!loaded" class="py-16 flex justify-center">
        <Icon name="loader" :size="20" class="animate-spin text-faint" />
      </div>
      <div v-else-if="logs.length" class="overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>群组</th>
              <th>发送者</th>
              <th>消息内容</th>
              <th>消息 ID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in logs" :key="l.id">
              <td class="text-dim text-xs whitespace-nowrap">{{ fmtDate(l.created_at) }}</td>
              <td>
                <div class="font-mono text-xs">{{ l.chat_id }}</div>
                <div v-if="l.topic_id" class="text-[11px] text-faint mt-0.5">话题 {{ l.topic_id }}</div>
              </td>
              <td>
                <div class="text-[13px]">{{ l.sender_name || '—' }}</div>
                <div class="text-[11px] text-faint font-mono mt-0.5">{{ l.sender_id }}</div>
              </td>
              <td>
                <div class="max-w-md truncate" :class="l.text ? '' : 'text-faint'" :title="l.text">
                  {{ l.text || '（媒体消息）' }}
                </div>
              </td>
              <td class="font-mono text-xs text-dim">{{ l.message_id }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="file-text" title="暂无消息日志" :hint="chatFilter ? '当前筛选条件下没有记录，试试重置筛选' : '监控群组产生消息后会记录在这里'" />
    </div>

    <TablePagination
      v-if="loaded && (page > 0 || logs.length)"
      :page="page"
      :has-more="logs.length >= pageSize"
      @change="p => { page = p; load() }"
    />
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api.js'
import { fmtDate } from '../format.js'
import Icon from '../components/Icon.vue'
import PageHeader from '../components/PageHeader.vue'
import EmptyState from '../components/EmptyState.vue'
import TablePagination from '../components/TablePagination.vue'

const toast = inject('toast')
const logs = ref([])
const loaded = ref(false)
const chatFilter = ref('')
const page = ref(0)
const pageSize = 50

async function load() {
  const params = { limit: pageSize, offset: page.value * pageSize }
  if (chatFilter.value) params.chat_id = chatFilter.value
  try {
    logs.value = await api.getLogs(params)
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loaded.value = true
  }
}

function search() {
  page.value = 0
  load()
}

function reset() {
  chatFilter.value = ''
  page.value = 0
  load()
}

onMounted(load)
</script>
