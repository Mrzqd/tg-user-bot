<template>
  <div class="fade-in">
    <PageHeader title="仪表盘" description="账号状态与核心数据总览" />

    <!-- 概览卡片 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
      <div class="card flex items-center gap-4">
        <div class="w-11 h-11 rounded-full bg-gradient-to-br from-accent to-violet flex items-center justify-center text-white text-lg font-bold shrink-0">
          {{ avatarChar }}
        </div>
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-[15px] font-semibold truncate">{{ status?.first_name || '未登录' }}</span>
            <span :class="status?.telegram_authorized ? 'badge-ok' : 'badge-err'">
              {{ status?.telegram_authorized ? '在线' : '离线' }}
            </span>
          </div>
          <div class="text-xs text-dim truncate mt-0.5">
            @{{ status?.username || '—' }} · {{ status?.user_id || '—' }}
          </div>
        </div>
      </div>

      <div v-for="stat in stats" :key="stat.label" class="card flex items-center gap-4">
        <div class="w-11 h-11 rounded-xl flex items-center justify-center shrink-0" :class="stat.tint">
          <Icon :name="stat.icon" :size="20" />
        </div>
        <div class="min-w-0">
          <div class="text-2xl font-bold leading-tight tabular-nums">{{ stat.value ?? '—' }}</div>
          <div class="text-xs text-dim mt-0.5">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <!-- Telegram 登录（未授权时） -->
    <div v-if="status && !status.telegram_authorized" class="card mb-6 max-w-2xl">
      <div class="flex items-center gap-2.5 mb-5">
        <div class="w-8 h-8 rounded-lg bg-accent/12 text-accent flex items-center justify-center">
          <Icon name="phone" :size="16" />
        </div>
        <div>
          <h3 class="text-sm font-semibold">登录 Telegram 账号</h3>
          <p class="text-xs text-faint">登录后机器人才能监控群组和自动回复</p>
        </div>
      </div>

      <!-- 第一步：手机号 -->
      <div v-if="loginStep === 'phone'" class="flex flex-col gap-4">
        <FormField label="手机号" hint="国际格式，含国家区号">
          <input v-model="loginForm.phone" class="input-base" placeholder="+8613800138000" @keydown.enter="sendCode" />
        </FormField>
        <div class="flex items-center gap-3">
          <button class="btn-primary" :disabled="loginBusy" @click="sendCode">
            <Icon v-if="loginBusy" name="loader" :size="14" class="animate-spin" />
            发送验证码
          </button>
          <button class="btn-ghost" @click="loginStep = 'code'">已有验证码？直接填写</button>
        </div>
      </div>

      <!-- 第二步：验证码 -->
      <div v-else-if="loginStep === 'code'" class="flex flex-col gap-4">
        <FormField label="验证码" :hint="loginForm.phone ? `验证码已发送至 ${loginForm.phone} 的 Telegram` : '查看 Telegram 官方消息获取验证码'">
          <input v-model="loginForm.code" class="input-base" placeholder="12345" @keydown.enter="signIn" />
        </FormField>
        <div class="flex items-center gap-3">
          <button class="btn-primary" :disabled="loginBusy" @click="signIn">
            <Icon v-if="loginBusy" name="loader" :size="14" class="animate-spin" />
            提交验证码
          </button>
          <button class="btn-ghost" :disabled="loginBusy" @click="loginStep = 'phone'">返回上一步</button>
        </div>
      </div>

      <!-- 第三步：二步验证密码 -->
      <div v-else class="flex flex-col gap-4">
        <FormField label="二步验证密码" hint="该账号开启了两步验证，需要输入云密码">
          <input v-model="loginForm.password" class="input-base" type="password" @keydown.enter="submitPassword" />
        </FormField>
        <div class="flex items-center gap-3">
          <button class="btn-primary" :disabled="loginBusy" @click="submitPassword">
            <Icon v-if="loginBusy" name="loader" :size="14" class="animate-spin" />
            提交密码
          </button>
        </div>
      </div>
    </div>

    <!-- 快速发送（已授权时） -->
    <div v-else-if="status?.telegram_authorized" class="card max-w-2xl">
      <div class="flex items-center gap-2.5 mb-5">
        <div class="w-8 h-8 rounded-lg bg-accent/12 text-accent flex items-center justify-center">
          <Icon name="message-circle" :size="16" />
        </div>
        <div>
          <h3 class="text-sm font-semibold">快速发送</h3>
          <p class="text-xs text-faint">以当前账号身份向任意会话发送消息</p>
        </div>
      </div>
      <div class="flex flex-col sm:flex-row gap-3">
        <FormField label="Chat ID" class="sm:w-48">
          <input v-model="sendForm.chat_id" class="input-base" placeholder="-1001234567890" />
        </FormField>
        <FormField label="消息内容" class="flex-1">
          <input v-model="sendForm.text" class="input-base" placeholder="输入消息内容，回车发送" @keydown.enter="send" />
        </FormField>
        <div class="flex sm:flex-col sm:justify-end">
          <button class="btn-primary" :disabled="sending" @click="send">
            <Icon :name="sending ? 'loader' : 'send'" :size="14" :class="sending ? 'animate-spin' : ''" />
            发送
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue'
import { api } from '../api.js'
import Icon from '../components/Icon.vue'
import PageHeader from '../components/PageHeader.vue'
import FormField from '../components/FormField.vue'

const toast = inject('toast')
const status = ref(null)
const sendForm = ref({ chat_id: '', text: '' })
const sending = ref(false)

const loginStep = ref('phone') // phone | code | password
const loginBusy = ref(false)
const loginForm = ref({ phone: '', code: '', password: '' })

const avatarChar = computed(() => (status.value?.first_name || '?').trim().charAt(0).toUpperCase())

const stats = computed(() => [
  { icon: 'users', label: '监控群组', value: status.value?.monitored_groups, tint: 'bg-accent/12 text-accent' },
  { icon: 'zap', label: '关键词规则', value: status.value?.keyword_rules, tint: 'bg-ok/12 text-ok' },
  { icon: 'clock', label: '定时任务', value: status.value?.scheduled_tasks, tint: 'bg-warn/12 text-warn' },
])

async function load() {
  try { status.value = await api.getStatus() } catch {}
}

async function loadTelegramAuth() {
  try {
    const auth = await api.getTelegramAuthStatus()
    if (auth.phone && !loginForm.value.phone) loginForm.value.phone = auth.phone
  } catch {}
}

async function sendCode() {
  if (!loginForm.value.phone) return toast('请输入手机号', 'error')
  loginBusy.value = true
  try {
    await api.sendTelegramCode({ phone: loginForm.value.phone })
    toast('验证码已发送')
    loginStep.value = 'code'
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loginBusy.value = false
  }
}

async function signIn() {
  if (!loginForm.value.code) return toast('请输入验证码', 'error')
  loginBusy.value = true
  try {
    const res = await api.signInTelegram({ code: loginForm.value.code })
    if (res.status === 'password_needed') {
      loginStep.value = 'password'
      toast('该账号需要二步验证密码')
      return
    }
    toast('Telegram 登录成功')
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loginBusy.value = false
  }
}

async function submitPassword() {
  if (!loginForm.value.password) return toast('请输入二步验证密码', 'error')
  loginBusy.value = true
  try {
    await api.signInTelegramPassword({ password: loginForm.value.password })
    toast('Telegram 登录成功')
    await load()
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loginBusy.value = false
  }
}

async function send() {
  if (!sendForm.value.chat_id || !sendForm.value.text) return
  sending.value = true
  try {
    await api.sendMessage({ chat_id: Number(sendForm.value.chat_id), text: sendForm.value.text })
    toast('消息已发送')
    sendForm.value.text = ''
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  await load()
  await loadTelegramAuth()
})
</script>
