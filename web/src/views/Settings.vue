<template>
  <div class="fade-in">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold">系统设置</h2>
      <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
    </div>

    <div class="card max-w-3xl">
      <h3 class="text-sm font-semibold text-accent mb-4">资源下载</h3>

      <div class="grid grid-cols-2 gap-4 mb-4">
        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">下载目标</span>
          <select v-model="form.target_type" class="input-base">
            <option value="local">本地目录</option>
            <option value="webdav">WebDAV</option>
          </select>
        </label>

        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">本地目录</span>
          <input v-model="form.local_path" class="input-base" placeholder="downloads 或 /data/downloads" />
        </label>
      </div>

      <div v-if="form.target_type === 'webdav'" class="space-y-4">
        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">WebDAV URL</span>
          <input v-model="form.webdav_url" class="input-base" placeholder="https://example.com/dav/" />
        </label>

        <div class="grid grid-cols-2 gap-4">
          <label class="block">
            <span class="text-xs text-dim mb-1.5 block">用户名</span>
            <input v-model="form.webdav_username" class="input-base" autocomplete="username" />
          </label>

          <label class="block">
            <span class="text-xs text-dim mb-1.5 block">密码</span>
            <input
              v-model="form.webdav_password"
              class="input-base"
              type="password"
              autocomplete="new-password"
              :placeholder="hasPassword ? '留空表示不修改' : ''"
            />
          </label>
        </div>

        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">远端目录</span>
          <input v-model="form.webdav_remote_path" class="input-base" placeholder="telegram/downloads" />
        </label>

        <div class="flex gap-5">
          <label class="inline-flex items-center gap-2 text-sm text-dim">
            <input v-model="form.keep_local" type="checkbox" />
            <span>上传后保留本地文件</span>
          </label>

          <label class="inline-flex items-center gap-2 text-sm text-dim">
            <input v-model="form.webdav_verify_ssl" type="checkbox" />
            <span>校验 SSL 证书</span>
          </label>
        </div>
      </div>

      <div class="mt-6 pt-5 border-t border-border">
        <h3 class="text-sm font-semibold text-accent mb-4">点赞下载</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label class="inline-flex items-center gap-2 text-sm text-dim md:mt-7">
            <input v-model="form.reaction_enabled" type="checkbox" />
            <span>启用表情监听</span>
          </label>

          <label class="block">
            <span class="text-xs text-dim mb-1.5 block">触发表情</span>
            <input v-model="form.reaction_emoji" class="input-base" placeholder="👍" />
          </label>

          <label class="block">
            <span class="text-xs text-dim mb-1.5 block">通知会话 ID</span>
            <input v-model.number="form.reaction_notify_chat_id" class="input-base" placeholder="-1001234567890" />
          </label>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, reactive, ref } from 'vue'
import { api } from '../api.js'

const saving = ref(false)
const hasPassword = ref(false)
const toast = inject('toast')
const form = reactive({
  target_type: 'local',
  local_path: 'downloads',
  keep_local: true,
  webdav_url: '',
  webdav_username: '',
  webdav_password: '',
  webdav_remote_path: '',
  webdav_verify_ssl: true,
  reaction_enabled: false,
  reaction_emoji: '👍',
  reaction_notify_chat_id: 0,
})

async function load() {
  try {
    const data = await api.getDownloadSettings()
    Object.assign(form, {
      target_type: data.target_type,
      local_path: data.local_path,
      keep_local: data.keep_local,
      webdav_url: data.webdav_url,
      webdav_username: data.webdav_username,
      webdav_password: '',
      webdav_remote_path: data.webdav_remote_path,
      webdav_verify_ssl: data.webdav_verify_ssl,
      reaction_enabled: data.reaction_enabled,
      reaction_emoji: data.reaction_emoji,
      reaction_notify_chat_id: data.reaction_notify_chat_id,
    })
    hasPassword.value = data.has_webdav_password
  } catch (e) {
    toast(e.message, 'error')
  }
}

async function save() {
  saving.value = true
  try {
    const data = await api.updateDownloadSettings(form)
    hasPassword.value = data.has_webdav_password
    form.webdav_password = ''
    toast('设置已保存')
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
