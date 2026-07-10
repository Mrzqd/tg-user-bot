<template>
  <div class="fade-in">
    <PageHeader title="监控群组" description="机器人只处理监控列表内群组的消息">
      <button class="btn-primary" @click="showAdd = true">
        <Icon name="plus" :size="15" />
        添加群组
      </button>
    </PageHeader>

    <div class="card-table">
      <div v-if="!loaded" class="py-16 flex justify-center">
        <Icon name="loader" :size="20" class="animate-spin text-faint" />
      </div>
      <div v-else-if="groups.length" class="overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>群组</th>
              <th>添加时间</th>
              <th>监控状态</th>
              <th class="w-20 !text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="g in groups" :key="g.chat_id">
              <td>
                <div class="font-medium">{{ g.title || '未命名群组' }}</div>
                <div class="text-[11px] text-faint font-mono mt-0.5">{{ g.chat_id }}</div>
              </td>
              <td class="text-dim text-xs whitespace-nowrap">{{ fmtDate(g.created_at) }}</td>
              <td>
                <div class="flex items-center gap-2.5">
                  <ToggleSwitch :model-value="g.is_active" @update:model-value="toggle(g)" />
                  <span class="text-xs" :class="g.is_active ? 'text-ok' : 'text-faint'">
                    {{ g.is_active ? '监控中' : '已暂停' }}
                  </span>
                </div>
              </td>
              <td>
                <div class="flex justify-end">
                  <button class="btn-icon-danger" title="移除" @click="remove(g)">
                    <Icon name="trash" :size="15" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="users" title="暂无监控群组" hint="添加群组后，机器人才会处理其中的消息。也可以在目标群里发送 .monitor add">
        <button class="btn-primary" @click="showAdd = true">
          <Icon name="plus" :size="15" />
          添加群组
        </button>
      </EmptyState>
    </div>

    <ModalDialog v-if="showAdd" title="添加监控群组" confirm-text="添加" :busy="adding" @close="showAdd = false" @confirm="add">
      <div class="flex flex-col gap-4">
        <FormField label="Chat ID" hint="超级群组通常以 -100 开头，可在群里发送 .monitor add 查询">
          <input v-model="form.chat_id" class="input-base" placeholder="-1001234567890" />
        </FormField>
        <FormField label="名称（可选）">
          <input v-model="form.title" class="input-base" placeholder="群组备注名称" />
        </FormField>
      </div>
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
import FormField from '../components/FormField.vue'

const toast = inject('toast')
const confirmDialog = inject('confirm')

const groups = ref([])
const loaded = ref(false)
const showAdd = ref(false)
const adding = ref(false)
const form = ref({ chat_id: '', title: '' })

async function load() {
  try {
    groups.value = await api.getGroups()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loaded.value = true
  }
}

async function add() {
  const chatId = String(form.value.chat_id).trim()
  if (!/^-?\d+$/.test(chatId)) return toast('Chat ID 必须为数字', 'error')
  adding.value = true
  try {
    await api.addGroup({ chat_id: Number(chatId), title: form.value.title.trim() })
    toast('群组已添加')
    showAdd.value = false
    form.value = { chat_id: '', title: '' }
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    adding.value = false
  }
}

async function toggle(g) {
  try {
    await api.toggleGroup(g.chat_id, !g.is_active)
    await load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

async function remove(g) {
  const ok = await confirmDialog(`确定移除对「${g.title || g.chat_id}」的监控？`, { title: '移除群组', confirmText: '移除' })
  if (!ok) return
  try {
    await api.removeGroup(g.chat_id)
    toast('群组已移除')
    await load()
  } catch (e) {
    toast(e.message, 'error')
  }
}

onMounted(load)
</script>
