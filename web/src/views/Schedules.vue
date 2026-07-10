<template>
  <div class="fade-in">
    <PageHeader title="定时任务" description="按 Cron 周期或指定时间自动发送消息（北京时间）">
      <button class="btn-primary" @click="openAdd">
        <Icon name="plus" :size="15" />
        添加任务
      </button>
    </PageHeader>

    <div class="card-table">
      <div v-if="!loaded" class="py-16 flex justify-center">
        <Icon name="loader" :size="20" class="animate-spin text-faint" />
      </div>
      <div v-else-if="list.length" class="overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>消息内容</th>
              <th>目标</th>
              <th>触发</th>
              <th>上次发送</th>
              <th>状态</th>
              <th class="w-24 !text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in list" :key="s.id">
              <td>
                <div class="max-w-56 truncate font-medium" :title="s.text">{{ s.text }}</div>
                <div class="text-[11px] text-faint mt-0.5">
                  #{{ s.id }}<span v-if="s.delete_after"> · 发送 {{ s.delete_after }}s 后自动删除</span>
                </div>
              </td>
              <td>
                <div class="font-mono text-xs">{{ s.chat_id }}</div>
                <div class="text-[11px] text-faint mt-0.5">{{ s.topic_id ? `话题 ${s.topic_id}` : '默认话题' }}</div>
              </td>
              <td>
                <span :class="s.cron_expr ? 'badge-accent' : 'badge-warn'">{{ s.cron_expr ? '周期' : '单次' }}</span>
                <div class="font-mono text-[11px] text-dim mt-1 whitespace-nowrap">{{ s.cron_expr || fmtDate(s.run_at) }}</div>
              </td>
              <td class="text-dim text-xs whitespace-nowrap">{{ s.last_sent_at ? fmtDate(s.last_sent_at) : '—' }}</td>
              <td>
                <ToggleSwitch :model-value="s.is_active" @update:model-value="toggle(s)" />
              </td>
              <td>
                <div class="flex justify-end gap-0.5">
                  <button class="btn-icon" title="编辑" @click="openEdit(s)">
                    <Icon name="pencil" :size="15" />
                  </button>
                  <button class="btn-icon-danger" title="删除" @click="remove(s)">
                    <Icon name="trash" :size="15" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="clock" title="暂无定时任务" hint="支持 Cron 周期任务、指定时间和相对延时的单次任务">
        <button class="btn-primary" @click="openAdd">
          <Icon name="plus" :size="15" />
          添加任务
        </button>
      </EmptyState>
    </div>

    <ModalDialog v-if="showAdd" title="添加定时任务" confirm-text="添加" :busy="saving" wide @close="showAdd = false" @confirm="add">
      <ScheduleForm v-model="form" />
    </ModalDialog>

    <ModalDialog v-if="showEdit" title="编辑定时任务" confirm-text="更新" :busy="saving" wide @close="showEdit = false" @confirm="update">
      <ScheduleForm v-model="editForm" />
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api.js'
import { fmtDate } from '../format.js'
import Icon from '../components/Icon.vue'
import PageHeader from '../components/PageHeader.vue'
import ModalDialog from '../components/ModalDialog.vue'
import ToggleSwitch from '../components/ToggleSwitch.vue'
import EmptyState from '../components/EmptyState.vue'
import ScheduleForm from '../components/ScheduleForm.vue'

const toast = inject('toast')
const confirmDialog = inject('confirm')

const list = ref([])
const loaded = ref(false)
const showAdd = ref(false)
const showEdit = ref(false)
const saving = ref(false)
const editingId = ref(null)

const mkForm = () => ({ chat_id: '', topic_id: 0, type: 'cron', cron_expr: '', run_at: '', delay: '', text: '', delete_after: 0 })
const form = ref(mkForm())
const editForm = ref(mkForm())

async function load() {
  try {
    list.value = await api.getSchedules()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loaded.value = true
  }
}

function openAdd() {
  form.value = mkForm()
  showAdd.value = true
}

function openEdit(s) {
  editingId.value = s.id
  editForm.value = {
    chat_id: String(s.chat_id),
    topic_id: s.topic_id || 0,
    type: s.cron_expr ? 'cron' : 'once',
    cron_expr: s.cron_expr || '',
    run_at: s.run_at ? s.run_at.slice(0, 16) : '',
    delay: '',
    text: s.text,
    delete_after: s.delete_after || 0,
  }
  showEdit.value = true
}

function parseDuration(s) {
  const m = s.match(/^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/i)
  if (!m || !m.slice(1).some(Boolean)) return null
  return ((+(m[1] || 0)) * 86400 + (+(m[2] || 0)) * 3600 + (+(m[3] || 0)) * 60 + (+(m[4] || 0))) * 1000
}

function toLocalISO(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function buildBody(f) {
  const chatId = String(f.chat_id).trim()
  if (!/^-?\d+$/.test(chatId)) throw new Error('Chat ID 必须为数字')
  if (!String(f.text).trim()) throw new Error('请输入消息内容')

  const body = { chat_id: Number(chatId), topic_id: f.topic_id || 0, text: f.text, delete_after: f.delete_after || 0 }
  if (f.type === 'cron') {
    if (!f.cron_expr.trim()) throw new Error('请输入 Cron 表达式')
    body.cron_expr = f.cron_expr
    body.run_at = null
  } else if (f.type === 'delay') {
    const ms = parseDuration((f.delay || '').trim())
    if (!ms) throw new Error('延时格式错误，示例：1d5h30m、2h、30s')
    body.run_at = toLocalISO(new Date(Date.now() + ms))
    body.cron_expr = null
  } else {
    if (!f.run_at) throw new Error('请选择执行时间')
    body.run_at = f.run_at
    body.cron_expr = null
  }
  return body
}

async function add() {
  saving.value = true
  try {
    await api.addSchedule(buildBody(form.value))
    toast('任务已添加')
    showAdd.value = false
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

async function update() {
  saving.value = true
  try {
    await api.updateSchedule(editingId.value, buildBody(editForm.value))
    toast('任务已更新')
    showEdit.value = false
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

async function toggle(s) {
  try {
    await api.toggleSchedule(s.id, !s.is_active)
    await load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

async function remove(s) {
  const ok = await confirmDialog(`确定删除定时任务 #${s.id}？删除后计时器会一并取消。`, { title: '删除定时任务', confirmText: '删除' })
  if (!ok) return
  try {
    await api.deleteSchedule(s.id)
    toast('任务已删除')
    await load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

onMounted(load)
</script>
