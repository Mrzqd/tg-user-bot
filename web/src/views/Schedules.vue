<template>
  <div class="fade-in">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold">定时任务</h2>
      <button class="btn-primary" @click="openAdd">+ 添加任务</button>
    </div>

    <div class="card overflow-x-auto">
      <table v-if="list.length">
        <thead><tr><th>#</th><th>Chat ID</th><th>话题</th><th>类型</th><th>触发条件</th><th>消息内容</th><th>自动删除</th><th>上次发送</th><th>状态</th><th class="w-32">操作</th></tr></thead>
        <tbody>
          <tr v-for="s in list" :key="s.id">
            <td class="font-mono text-xs">{{ s.id }}</td>
            <td class="font-mono text-xs">{{ s.chat_id }}</td>
            <td class="font-mono text-xs">{{ s.topic_id ? s.topic_id : '—' }}</td>
            <td><span class="badge" :class="s.cron_expr ? 'bg-accent/15 text-accent' : 'bg-warn/15 text-warn'">{{ s.cron_expr ? '周期' : '单次' }}</span></td>
            <td class="font-mono text-xs">{{ s.cron_expr || fmt(s.run_at) }}</td>
            <td class="max-w-40 truncate">{{ s.text }}</td>
            <td>{{ s.delete_after ? s.delete_after + '秒' : '—' }}</td>
            <td class="text-dim text-xs">{{ s.last_sent_at ? fmt(s.last_sent_at) : '—' }}</td>
            <td><span :class="s.is_active ? 'badge-on' : 'badge-off'">{{ s.is_active ? '启用' : '停用' }}</span></td>
            <td class="flex gap-1">
              <button class="btn-icon" @click="openEdit(s)" title="编辑">✎</button>
              <button class="btn-icon" @click="toggle(s)">{{ s.is_active ? '⏸' : '▶' }}</button>
              <button class="btn-icon hover:!text-err" @click="remove(s)" title="删除">✕</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-center py-10 text-dim text-sm">暂无定时任务</div>
    </div>

    <!-- 添加弹窗 -->
    <ModalDialog v-if="showAdd" title="添加定时任务" @close="showAdd = false" @confirm="add">
      <ScheduleForm v-model="form" />
    </ModalDialog>

    <!-- 编辑弹窗 -->
    <ModalDialog v-if="showEdit" title="编辑定时任务" confirm-text="更新" @close="showEdit = false" @confirm="update">
      <ScheduleForm v-model="editForm" />
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api.js'
import ModalDialog from '../components/ModalDialog.vue'
import ScheduleForm from '../components/ScheduleForm.vue'

const toast = inject('toast')
const list = ref([])
const showAdd = ref(false)
const showEdit = ref(false)
const editingId = ref(null)
const mkForm = () => ({ chat_id: '', topic_id: 0, type: 'cron', cron_expr: '', run_at: '', delay: '', text: '', delete_after: 0 })
const form = ref(mkForm())
const editForm = ref(mkForm())
const fmt = (s) => s ? new Date(s).toLocaleString('zh-CN') : '—'

async function load() { try { list.value = await api.getSchedules() } catch (e) { toast(e.message, 'error') } }
function openAdd() { form.value = mkForm(); showAdd.value = true }

function openEdit(s) {
  editingId.value = s.id
  editForm.value = {
    chat_id: String(s.chat_id),
    topic_id: s.topic_id || 0,
    type: s.cron_expr ? 'cron' : 'once',
    cron_expr: s.cron_expr || '',
    run_at: s.run_at ? s.run_at.slice(0, 16) : '',
    text: s.text,
    delete_after: s.delete_after || 0,
  }
  showEdit.value = true
}

function parseDuration(s) {
  const m = s.match(/^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/i)
  if (!m || !m.slice(1).some(Boolean)) return null
  return ((+(m[1]||0))*86400 + (+(m[2]||0))*3600 + (+(m[3]||0))*60 + (+(m[4]||0))) * 1000
}

function toLocalISO(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function buildBody(f) {
  const body = { chat_id: Number(f.chat_id), topic_id: f.topic_id || 0, text: f.text, delete_after: f.delete_after || 0 }
  if (f.type === 'cron') {
    body.cron_expr = f.cron_expr; body.run_at = null
  } else if (f.type === 'delay') {
    const ms = parseDuration(f.delay || '')
    if (!ms) throw new Error('延时格式错误，示例: 1d5h30m、2h、30s')
    body.run_at = toLocalISO(new Date(Date.now() + ms)); body.cron_expr = null
  } else {
    body.run_at = f.run_at || null; body.cron_expr = null
  }
  return body
}

async function add() {
  try { await api.addSchedule(buildBody(form.value)); toast('任务已添加'); showAdd.value = false; await load() }
  catch (e) { toast(e.message, 'error') }
}

async function update() {
  try { await api.updateSchedule(editingId.value, buildBody(editForm.value)); toast('任务已更新'); showEdit.value = false; await load() }
  catch (e) { toast(e.message, 'error') }
}

async function toggle(s) { try { await api.toggleSchedule(s.id, !s.is_active); await load() } catch (e) { toast(e.message, 'error') } }

async function remove(s) {
  if (!confirm(`确定删除定时任务 #${s.id}？`)) return
  try { await api.deleteSchedule(s.id); toast('任务已删除'); await load() } catch (e) { toast(e.message, 'error') }
}

onMounted(load)
</script>
