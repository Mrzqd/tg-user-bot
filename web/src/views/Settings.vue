<template>
  <div class="fade-in">
    <PageHeader title="系统设置" description="媒体下载的存储方式与点赞下载">
      <button class="btn-primary" :disabled="saving" @click="save">
        <Icon v-if="saving" name="loader" :size="14" class="animate-spin" />
        {{ saving ? '保存中…' : '保存设置' }}
      </button>
    </PageHeader>

    <div class="flex flex-col gap-5 max-w-3xl">
      <!-- 存储目标 -->
      <div class="card">
        <div class="flex items-center gap-2.5 mb-5">
          <div class="w-8 h-8 rounded-lg bg-accent/12 text-accent flex items-center justify-center">
            <Icon name="download" :size="16" />
          </div>
          <div>
            <h3 class="text-sm font-semibold">存储目标</h3>
            <p class="text-xs text-faint">选择下载的媒体文件保存到哪里</p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
          <button
            v-for="opt in targetOptions"
            :key="opt.value"
            type="button"
            class="flex items-start gap-3 p-3.5 rounded-xl border text-left cursor-pointer transition-all duration-150 bg-transparent"
            :class="form.target_type === opt.value
              ? 'border-accent/70 bg-accent/8 ring-1 ring-accent/30'
              : 'border-border hover:border-border-strong hover:bg-bg-hover/50'"
            @click="form.target_type = opt.value"
          >
            <Icon :name="opt.icon" :size="18" class="mt-0.5 shrink-0" :class="form.target_type === opt.value ? 'text-accent' : 'text-faint'" />
            <span>
              <span class="block text-sm font-medium text-white">{{ opt.label }}</span>
              <span class="block text-[11px] text-dim mt-0.5">{{ opt.desc }}</span>
            </span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="本地目录" hint="相对路径基于程序运行目录">
            <input v-model="form.local_path" class="input-base" placeholder="downloads 或 /data/downloads" />
          </FormField>
        </div>

        <div v-if="form.target_type !== 'local'" class="flex items-center justify-between gap-4 mt-4 pt-4 border-t border-border/60">
          <div>
            <div class="text-sm font-medium">上传后保留本地文件</div>
            <div class="text-xs text-faint mt-0.5">关闭后，上传成功会删除本地暂存文件</div>
          </div>
          <ToggleSwitch v-model="form.keep_local" />
        </div>
      </div>

      <!-- WebDAV -->
      <div v-if="form.target_type === 'webdav'" class="card">
        <div class="flex items-center gap-2.5 mb-5">
          <div class="w-8 h-8 rounded-lg bg-violet/12 text-violet flex items-center justify-center">
            <Icon name="cloud" :size="16" />
          </div>
          <div>
            <h3 class="text-sm font-semibold">WebDAV 配置</h3>
            <p class="text-xs text-faint">下载完成后上传到 WebDAV 服务器</p>
          </div>
        </div>

        <div class="flex flex-col gap-4">
          <FormField label="WebDAV URL">
            <input v-model="form.webdav_url" class="input-base" placeholder="https://example.com/dav/" />
          </FormField>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="用户名">
              <input v-model="form.webdav_username" class="input-base" autocomplete="username" />
            </FormField>
            <FormField label="密码">
              <input
                v-model="form.webdav_password"
                class="input-base"
                type="password"
                autocomplete="new-password"
                :placeholder="hasPassword ? '已设置，留空表示不修改' : ''"
              />
            </FormField>
          </div>

          <FormField label="远端目录">
            <input v-model="form.webdav_remote_path" class="input-base" placeholder="telegram/downloads" />
          </FormField>

          <div class="flex items-center justify-between gap-4">
            <div>
              <div class="text-sm font-medium">校验 SSL 证书</div>
              <div class="text-xs text-faint mt-0.5">自签名证书的服务器可关闭</div>
            </div>
            <ToggleSwitch v-model="form.webdav_verify_ssl" />
          </div>

          <div class="flex flex-col gap-2 pt-3 border-t border-border/60 sm:flex-row sm:items-center sm:justify-between">
            <button class="btn-ghost w-fit" :disabled="testingWebDav" @click="testWebDav">
              <Icon :name="testingWebDav ? 'loader' : 'check'" :size="14" :class="testingWebDav ? 'animate-spin' : ''" />
              {{ testingWebDav ? '测试中…' : '测试连接' }}
            </button>
            <div v-if="webDavTestMessage" class="flex items-start gap-1.5 text-xs" :class="webDavTestOk ? 'text-ok' : 'text-err'">
              <Icon :name="webDavTestOk ? 'check-circle' : 'alert-circle'" :size="14" class="mt-0.5 shrink-0" />
              <span class="break-all">{{ webDavTestMessage }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- S3 -->
      <div v-if="form.target_type === 's3'" class="card">
        <div class="flex items-center gap-2.5 mb-5">
          <div class="w-8 h-8 rounded-lg bg-warn/12 text-warn flex items-center justify-center">
            <Icon name="database" :size="16" />
          </div>
          <div>
            <h3 class="text-sm font-semibold">S3 对象存储配置</h3>
            <p class="text-xs text-faint">兼容 AWS S3、R2、MinIO 等对象存储</p>
          </div>
        </div>

        <div class="flex flex-col gap-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Endpoint URL">
              <input v-model="form.s3_endpoint_url" class="input-base" placeholder="https://s3.example.com" />
            </FormField>
            <FormField label="Region">
              <input v-model="form.s3_region" class="input-base" placeholder="auto 或 us-east-1" />
            </FormField>
            <FormField label="Bucket">
              <input v-model="form.s3_bucket" class="input-base" placeholder="telegram-downloads" />
            </FormField>
            <FormField label="远端目录">
              <input v-model="form.s3_prefix" class="input-base" placeholder="local/tg" />
            </FormField>
            <FormField label="Access Key">
              <input v-model="form.s3_access_key_id" class="input-base" autocomplete="username" />
            </FormField>
            <FormField label="Secret Key">
              <input
                v-model="form.s3_secret_access_key"
                class="input-base"
                type="password"
                autocomplete="new-password"
                :placeholder="hasS3Secret ? '已设置，留空表示不修改' : ''"
              />
            </FormField>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FormField label="地址风格">
              <select v-model="form.s3_addressing_style" class="input-base">
                <option value="auto">自动</option>
                <option value="path">Path style</option>
                <option value="virtual">Virtual host</option>
              </select>
            </FormField>
            <FormField label="分片大小（MB）">
              <input v-model.number="form.s3_multipart_chunk_mb" class="input-base" type="number" min="5" max="512" />
            </FormField>
            <FormField label="上传并发数">
              <input v-model.number="form.s3_max_concurrency" class="input-base" type="number" min="1" max="64" />
            </FormField>
          </div>
        </div>
      </div>

      <!-- 点赞下载 -->
      <div class="card">
        <div class="flex items-center gap-2.5 mb-5">
          <div class="w-8 h-8 rounded-lg bg-err/12 text-err flex items-center justify-center">
            <Icon name="heart" :size="16" />
          </div>
          <div>
            <h3 class="text-sm font-semibold">点赞下载</h3>
            <p class="text-xs text-faint">给任意消息添加表情回应即可触发媒体下载</p>
          </div>
        </div>

        <div class="flex flex-col gap-4">
          <div class="flex items-center justify-between gap-4">
            <div>
              <div class="text-sm font-medium">启用表情监听</div>
              <div class="text-xs text-faint mt-0.5">监听我自己添加的任意表情回应</div>
            </div>
            <ToggleSwitch v-model="form.reaction_enabled" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="通知会话 ID" hint="下载进度与结果会发送到该会话；为 0 时点赞下载不生效">
              <input v-model="form.reaction_notify_chat_id" class="input-base" placeholder="-1001234567890" />
            </FormField>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, reactive, ref } from 'vue'
import { api } from '../api.js'
import Icon from '../components/Icon.vue'
import PageHeader from '../components/PageHeader.vue'
import FormField from '../components/FormField.vue'
import ToggleSwitch from '../components/ToggleSwitch.vue'

const toast = inject('toast')
const saving = ref(false)
const testingWebDav = ref(false)
const webDavTestMessage = ref('')
const webDavTestOk = ref(false)
const hasPassword = ref(false)
const hasS3Secret = ref(false)

const targetOptions = [
  { value: 'local', label: '本地目录', desc: '仅保存到服务器本地磁盘', icon: 'hard-drive' },
  { value: 'webdav', label: 'WebDAV', desc: '上传到 WebDAV 网盘', icon: 'cloud' },
  { value: 's3', label: 'S3 对象存储', desc: '上传到 S3 兼容存储', icon: 'database' },
]

const form = reactive({
  target_type: 'local',
  local_path: 'downloads',
  keep_local: true,
  webdav_url: '',
  webdav_username: '',
  webdav_password: '',
  webdav_remote_path: '',
  webdav_verify_ssl: true,
  s3_endpoint_url: '',
  s3_region: '',
  s3_bucket: '',
  s3_access_key_id: '',
  s3_secret_access_key: '',
  s3_prefix: '',
  s3_addressing_style: 'auto',
  s3_multipart_chunk_mb: 16,
  s3_max_concurrency: 8,
  reaction_enabled: false,
  reaction_emoji: '👍',
  reaction_notify_chat_id: 0,
})

function toPayload() {
  return {
    ...form,
    reaction_notify_chat_id: Number(form.reaction_notify_chat_id) || 0,
    s3_multipart_chunk_mb: Number(form.s3_multipart_chunk_mb) || 16,
    s3_max_concurrency: Number(form.s3_max_concurrency) || 8,
  }
}

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
      s3_endpoint_url: data.s3_endpoint_url,
      s3_region: data.s3_region,
      s3_bucket: data.s3_bucket,
      s3_access_key_id: data.s3_access_key_id,
      s3_secret_access_key: '',
      s3_prefix: data.s3_prefix,
      s3_addressing_style: data.s3_addressing_style,
      s3_multipart_chunk_mb: data.s3_multipart_chunk_mb,
      s3_max_concurrency: data.s3_max_concurrency,
      reaction_enabled: data.reaction_enabled,
      reaction_emoji: data.reaction_emoji,
      reaction_notify_chat_id: data.reaction_notify_chat_id,
    })
    hasPassword.value = data.has_webdav_password
    hasS3Secret.value = data.has_s3_secret_access_key
  } catch (e) {
    toast(e.message, 'error')
  }
}

async function save() {
  saving.value = true
  try {
    const data = await api.updateDownloadSettings(toPayload())
    hasPassword.value = data.has_webdav_password
    hasS3Secret.value = data.has_s3_secret_access_key
    form.webdav_password = ''
    form.s3_secret_access_key = ''
    toast('设置已保存')
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

async function testWebDav() {
  testingWebDav.value = true
  webDavTestMessage.value = ''
  webDavTestOk.value = false
  try {
    const data = await api.testWebDavSettings(toPayload())
    webDavTestOk.value = true
    webDavTestMessage.value = data.target_url ? `${data.message}: ${data.target_url}` : data.message
    toast('WebDAV 测试成功')
  } catch (e) {
    webDavTestMessage.value = e.message
    toast(e.message, 'error')
  } finally {
    testingWebDav.value = false
  }
}

onMounted(load)
</script>
