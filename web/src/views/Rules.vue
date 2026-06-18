<template>
  <div class="fade-in">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold">关键词规则</h2>
      <button class="btn-primary" @click="openAdd">+ 添加规则</button>
    </div>
    <div class="card overflow-x-auto">
      <table v-if="rules.length">
        <thead><tr><th>#</th><th>关键词</th><th>动作</th><th>回复/按钮</th><th>条件</th><th>作用域</th><th>话题</th><th>正则</th><th>发送方式</th><th>延迟</th><th>自动删除</th><th>状态</th><th class="w-32">操作</th></tr></thead>
        <tbody>
          <tr v-for="r in rules" :key="r.id">
            <td class="font-mono text-xs">{{ r.id }}</td>
            <td class="font-mono text-xs text-accent max-w-36 truncate">{{ r.keyword }}</td>
            <td><span class="badge text-xs" :class="r.action === 'click_button' ? 'bg-warn/15 text-warn' : 'bg-accent/15 text-accent'">{{ r.action === 'click_button' ? '点击按钮' : '回复' }}</span></td>
            <td class="max-w-40 truncate text-xs">{{ r.action === 'click_button' ? (r.click_text || '第一个按钮') + (r.reply_text ? ' + ' + r.reply_text : '') : r.reply_text }}</td>
            <td class="max-w-32 truncate text-xs font-mono" :title="r.condition">{{ r.condition || '—' }}</td>
            <td class="font-mono text-xs">{{ r.chat_id === 0 ? '全部' : r.chat_id }}</td>
            <td class="font-mono text-xs">{{ r.topic_id ? r.topic_id : '全部' }}</td>
            <td>{{ r.is_regex ? '是' : '—' }}</td>
            <td><span class="badge text-xs" :class="r.no_quote ? 'bg-warn/15 text-warn' : 'bg-accent/15 text-accent'">{{ r.no_quote ? '直发' : '引用' }}</span></td>
            <td>{{ r.reply_delay ? r.reply_delay + '秒' : '—' }}</td>
            <td>{{ r.delete_after ? r.delete_after + '秒' : '—' }}</td>
            <td><span :class="r.is_active ? 'badge-on' : 'badge-off'">{{ r.is_active ? '启用' : '停用' }}</span></td>
            <td class="flex gap-1">
              <button class="btn-icon" @click="openEdit(r)" title="编辑">✎</button>
              <button class="btn-icon" @click="toggle(r)">{{ r.is_active ? '⏸' : '▶' }}</button>
              <button class="btn-icon hover:!text-err" @click="remove(r)" title="删除">✕</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-center py-10 text-dim text-sm">暂无关键词规则</div>
    </div>

    <ModalDialog v-if="showAdd" title="添加关键词规则" @close="showAdd = false" @confirm="add">
      <RuleForm v-model="form" />
    </ModalDialog>

    <ModalDialog v-if="showEdit" title="编辑关键词规则" confirm-text="更新" @close="showEdit = false" @confirm="update">
      <RuleForm v-model="editForm" />
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api.js'
import ModalDialog from '../components/ModalDialog.vue'
import RuleForm from '../components/RuleForm.vue'

const toast = inject('toast')
const rules = ref([])
const showAdd = ref(false)
const showEdit = ref(false)
const editingId = ref(null)
const mkForm = () => ({ keyword: '', reply_text: '', chat_id: 0, topic_id: 0, action: 'reply', click_text: '', condition: '', is_regex: false, no_quote: false, reply_delay: 0, delete_after: 0 })
const form = ref(mkForm())
const editForm = ref(mkForm())

async function load() { try { rules.value = await api.getRules() } catch (e) { toast(e.message, 'error') } }
function openAdd() { form.value = mkForm(); showAdd.value = true }

function openEdit(r) {
  editingId.value = r.id
  editForm.value = {
    keyword: r.keyword,
    reply_text: r.reply_text,
    chat_id: r.chat_id,
    topic_id: r.topic_id || 0,
    action: r.action || 'reply',
    click_text: r.click_text || '',
    condition: r.condition || '',
    is_regex: r.is_regex,
    no_quote: r.no_quote || false,
    reply_delay: r.reply_delay || 0,
    delete_after: r.delete_after || 0,
  }
  showEdit.value = true
}

async function add() {
  try {
    await api.addRule({ keyword: form.value.keyword, reply_text: form.value.reply_text, chat_id: Number(form.value.chat_id) || 0, topic_id: form.value.topic_id || 0, action: form.value.action || 'reply', click_text: form.value.click_text || '', condition: form.value.condition || '', is_regex: form.value.is_regex, no_quote: form.value.no_quote || false, reply_delay: form.value.reply_delay || 0, delete_after: form.value.delete_after || 0 })
    toast('规则已添加'); showAdd.value = false; await load()
  } catch (e) { toast(e.message, 'error') }
}

async function update() {
  try {
    await api.updateRule(editingId.value, { keyword: editForm.value.keyword, reply_text: editForm.value.reply_text, chat_id: Number(editForm.value.chat_id) || 0, topic_id: editForm.value.topic_id || 0, action: editForm.value.action || 'reply', click_text: editForm.value.click_text || '', condition: editForm.value.condition || '', is_regex: editForm.value.is_regex, no_quote: editForm.value.no_quote || false, reply_delay: editForm.value.reply_delay || 0, delete_after: editForm.value.delete_after || 0 })
    toast('规则已更新'); showEdit.value = false; await load()
  } catch (e) { toast(e.message, 'error') }
}

async function toggle(r) { try { await api.toggleRule(r.id, !r.is_active); await load() } catch (e) { toast(e.message, 'error') } }
async function remove(r) {
  if (!confirm(`确定删除规则 #${r.id}？`)) return
  try { await api.deleteRule(r.id); toast('规则已删除'); await load() } catch (e) { toast(e.message, 'error') }
}

onMounted(load)
</script>
