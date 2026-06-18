<template>
  <div class="fade-in">
    <div class="flex items-center justify-between mb-6"><h2 class="text-xl font-semibold">仪表盘</h2></div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="card">
        <div class="text-[11px] text-dim uppercase tracking-wide">账号</div>
        <div class="text-lg font-bold text-accent mt-1">{{ status?.first_name || '—' }}</div>
        <div class="text-xs text-dim mt-0.5">@{{ status?.username || '—' }} · {{ status?.user_id || '—' }}</div>
      </div>
      <div class="card">
        <div class="text-[11px] text-dim uppercase tracking-wide">监控群组</div>
        <div class="text-3xl font-bold text-accent mt-1">{{ status?.monitored_groups ?? '—' }}</div>
      </div>
      <div class="card">
        <div class="text-[11px] text-dim uppercase tracking-wide">关键词规则</div>
        <div class="text-3xl font-bold text-ok mt-1">{{ status?.keyword_rules ?? '—' }}</div>
      </div>
      <div class="card">
        <div class="text-[11px] text-dim uppercase tracking-wide">定时任务</div>
        <div class="text-3xl font-bold text-warn mt-1">{{ status?.scheduled_tasks ?? '—' }}</div>
      </div>
    </div>
    <div class="card">
      <h3 class="text-sm font-semibold mb-4">快速发送</h3>
      <div class="flex gap-3 flex-wrap">
        <div class="flex flex-col gap-1 min-w-40">
          <label class="text-xs text-dim">Chat ID</label>
          <input class="input-base" v-model="sendForm.chat_id" placeholder="-1001234567890" />
        </div>
        <div class="flex flex-col gap-1 flex-1 min-w-60">
          <label class="text-xs text-dim">消息内容</label>
          <input class="input-base" v-model="sendForm.text" placeholder="输入消息内容" @keydown.enter="send" />
        </div>
        <div class="flex flex-col justify-end">
          <button class="btn-primary" @click="send" :disabled="sending">发送</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api.js'
const toast = inject('toast')
const status = ref(null)
const sendForm = ref({ chat_id: '', text: '' })
const sending = ref(false)
async function load() { try { status.value = await api.getStatus() } catch {} }
async function send() {
  if (!sendForm.value.chat_id || !sendForm.value.text) return
  sending.value = true
  try { await api.sendMessage({ chat_id: Number(sendForm.value.chat_id), text: sendForm.value.text }); toast('消息已发送'); sendForm.value.text = '' }
  catch (e) { toast(e.message, 'error') } finally { sending.value = false }
}
onMounted(load)
</script>
