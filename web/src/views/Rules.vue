<template>
  <div class="fade-in">
    <PageHeader title="关键词规则" description="命中关键词后自动回复或点击按钮">
      <button class="btn-primary" @click="openAdd">
        <Icon name="plus" :size="15" />
        添加规则
      </button>
    </PageHeader>

    <div class="card-table">
      <div v-if="!loaded" class="py-16 flex justify-center">
        <Icon name="loader" :size="20" class="animate-spin text-faint" />
      </div>
      <div v-else-if="rules.length" class="overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>关键词</th>
              <th>动作</th>
              <th>作用域</th>
              <th>触发条件</th>
              <th>行为</th>
              <th>状态</th>
              <th class="w-24 !text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rules" :key="r.id">
              <td>
                <div class="flex items-center gap-1.5">
                  <code class="font-mono text-xs text-accent-light max-w-40 truncate" :title="r.keyword">{{ r.keyword }}</code>
                  <span v-if="r.is_regex" class="tag !text-accent-light !border-accent/30">正则</span>
                </div>
                <div class="text-[11px] text-faint mt-0.5">#{{ r.id }}</div>
              </td>
              <td>
                <span :class="r.action === 'click_button' ? 'badge-warn' : 'badge-accent'">
                  {{ r.action === 'click_button' ? '点击按钮' : '文字回复' }}
                </span>
                <div class="text-[11px] text-dim max-w-44 truncate mt-1" :title="actionContent(r)">{{ actionContent(r) }}</div>
              </td>
              <td>
                <div class="font-mono text-xs">{{ r.chat_id === 0 ? '全部群组' : r.chat_id }}</div>
                <div class="text-[11px] text-faint mt-0.5">{{ r.topic_id ? `话题 ${r.topic_id}` : '全部话题' }}</div>
              </td>
              <td>
                <code v-if="r.condition" class="font-mono text-[11px] text-dim block max-w-36 truncate" :title="r.condition">{{ r.condition }}</code>
                <span v-else class="text-faint text-xs">—</span>
              </td>
              <td>
                <div class="flex flex-wrap gap-1">
                  <span class="tag">{{ r.no_quote ? '直发' : '引用' }}</span>
                  <span v-if="r.reply_delay" class="tag">延迟 {{ r.reply_delay }}s</span>
                  <span v-if="r.delete_after" class="tag">{{ r.delete_after }}s 后删</span>
                </div>
              </td>
              <td>
                <ToggleSwitch :model-value="r.is_active" @update:model-value="toggle(r)" />
              </td>
              <td>
                <div class="flex justify-end gap-0.5">
                  <button class="btn-icon" title="编辑" @click="openEdit(r)">
                    <Icon name="pencil" :size="15" />
                  </button>
                  <button class="btn-icon-danger" title="删除" @click="remove(r)">
                    <Icon name="trash" :size="15" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="zap" title="暂无关键词规则" hint="添加规则后，机器人会在监控群组中自动响应命中的消息">
        <button class="btn-primary" @click="openAdd">
          <Icon name="plus" :size="15" />
          添加规则
        </button>
      </EmptyState>
    </div>

    <ModalDialog v-if="showAdd" title="添加关键词规则" confirm-text="添加" :busy="saving" wide @close="showAdd = false" @confirm="add">
      <RuleForm v-model="form" />
    </ModalDialog>

    <ModalDialog v-if="showEdit" title="编辑关键词规则" confirm-text="更新" :busy="saving" wide @close="showEdit = false" @confirm="update">
      <RuleForm v-model="editForm" />
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api.js'
import Icon from '../components/Icon.vue'
import PageHeader from '../components/PageHeader.vue'
import ModalDialog from '../components/ModalDialog.vue'
import ToggleSwitch from '../components/ToggleSwitch.vue'
import EmptyState from '../components/EmptyState.vue'
import RuleForm from '../components/RuleForm.vue'

const toast = inject('toast')
const confirmDialog = inject('confirm')

const rules = ref([])
const loaded = ref(false)
const showAdd = ref(false)
const showEdit = ref(false)
const saving = ref(false)
const editingId = ref(null)

const mkForm = () => ({
  keyword: '', reply_text: '', chat_id: 0, topic_id: 0, action: 'reply',
  click_text: '', condition: '', is_regex: false, no_quote: false,
  reply_delay: 0, delete_after: 0,
})
const form = ref(mkForm())
const editForm = ref(mkForm())

const actionContent = (r) => r.action === 'click_button'
  ? `点击「${r.click_text || '第一个按钮'}」${r.reply_text ? `，附加回复 ${r.reply_text}` : ''}`
  : r.reply_text

function toPayload(f) {
  return {
    keyword: f.keyword,
    reply_text: f.reply_text,
    chat_id: Number(f.chat_id) || 0,
    topic_id: f.topic_id || 0,
    action: f.action || 'reply',
    click_text: f.click_text || '',
    condition: f.condition || '',
    is_regex: Boolean(f.is_regex),
    no_quote: Boolean(f.no_quote),
    reply_delay: f.reply_delay || 0,
    delete_after: f.delete_after || 0,
  }
}

function validate(f) {
  if (!String(f.keyword).trim()) return '请输入关键词'
  if (f.action !== 'click_button' && !String(f.reply_text).trim()) return '请输入回复内容'
  return ''
}

async function load() {
  try {
    rules.value = await api.getRules()
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
  const err = validate(form.value)
  if (err) return toast(err, 'error')
  saving.value = true
  try {
    await api.addRule(toPayload(form.value))
    toast('规则已添加')
    showAdd.value = false
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

async function update() {
  const err = validate(editForm.value)
  if (err) return toast(err, 'error')
  saving.value = true
  try {
    await api.updateRule(editingId.value, toPayload(editForm.value))
    toast('规则已更新')
    showEdit.value = false
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

async function toggle(r) {
  try {
    await api.toggleRule(r.id, !r.is_active)
    await load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

async function remove(r) {
  const ok = await confirmDialog(`确定删除规则 #${r.id}（${r.keyword}）？`, { title: '删除规则', confirmText: '删除' })
  if (!ok) return
  try {
    await api.deleteRule(r.id)
    toast('规则已删除')
    await load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

onMounted(load)
</script>
