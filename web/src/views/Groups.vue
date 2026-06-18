<template>
  <div class="fade-in">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold">监控群组</h2>
      <button class="btn-primary" @click="showAdd = true">+ 添加群组</button>
    </div>
    <div class="card overflow-x-auto">
      <table v-if="groups.length">
        <thead><tr><th>Chat ID</th><th>名称</th><th>状态</th><th>创建时间</th><th class="w-24">操作</th></tr></thead>
        <tbody>
          <tr v-for="g in groups" :key="g.chat_id">
            <td class="font-mono text-xs">{{ g.chat_id }}</td>
            <td>{{ g.title || '—' }}</td>
            <td><span :class="g.is_active ? 'badge-on' : 'badge-off'">{{ g.is_active ? '启用' : '停用' }}</span></td>
            <td class="text-dim text-xs">{{ fmt(g.created_at) }}</td>
            <td class="flex gap-1">
              <button class="btn-icon" @click="toggle(g)" :title="g.is_active ? '暂停' : '恢复'">{{ g.is_active ? '⏸' : '▶' }}</button>
              <button class="btn-icon hover:!text-err" @click="remove(g)" title="删除">✕</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-center py-10 text-dim text-sm">暂无监控群组</div>
    </div>
    <ModalDialog v-if="showAdd" title="添加监控群组" @close="showAdd = false" @confirm="add">
      <div class="flex gap-3">
        <div class="flex-1 flex flex-col gap-1">
          <label class="text-xs text-dim">Chat ID</label>
          <input class="input-base" v-model="form.chat_id" placeholder="-1001234567890" />
        </div>
        <div class="flex-1 flex flex-col gap-1">
          <label class="text-xs text-dim">名称（可选）</label>
          <input class="input-base" v-model="form.title" placeholder="群组名称" />
        </div>
      </div>
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api.js'
import ModalDialog from '../components/ModalDialog.vue'
const toast = inject('toast')
const groups = ref([])
const showAdd = ref(false)
const form = ref({ chat_id: '', title: '' })
const fmt = (s) => s ? new Date(s).toLocaleString('zh-CN') : '—'
async function load() { try { groups.value = await api.getGroups() } catch (e) { toast(e.message, 'error') } }
async function add() {
  try { await api.addGroup({ chat_id: Number(form.value.chat_id), title: form.value.title }); toast('群组已添加'); showAdd.value = false; form.value = { chat_id: '', title: '' }; await load() }
  catch (e) { toast(e.message, 'error') }
}
async function toggle(g) { try { await api.toggleGroup(g.chat_id, !g.is_active); await load() } catch (e) { toast(e.message, 'error') } }
async function remove(g) {
  if (!confirm(`确定移除群组 ${g.chat_id}？`)) return
  try { await api.removeGroup(g.chat_id); toast('群组已移除'); await load() } catch (e) { toast(e.message, 'error') }
}
onMounted(load)
</script>
