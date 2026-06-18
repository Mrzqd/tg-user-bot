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
    <div v-if="!status?.telegram_authorized" class="card mb-6">
      <h3 class="text-sm font-semibold mb-4">Telegram 登录</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">手机号</span>
          <input class="input-base" v-model="loginForm.phone" placeholder="+8613800138000" />
        </label>
        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">验证码</span>
          <input class="input-base" v-model="loginForm.code" placeholder="12345" />
        </label>
        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">二步密码</span>
          <input class="input-base" v-model="loginForm.password" type="password" placeholder="需要时填写" />
        </label>
      </div>
      <div class="flex gap-3 mt-4">
        <button class="btn-primary" :disabled="loginBusy" @click="sendCode">发送验证码</button>
        <button class="btn-primary" :disabled="loginBusy" @click="signIn">提交验证码</button>
        <button v-if="passwordNeeded" class="btn-primary" :disabled="loginBusy" @click="submitPassword">提交二步密码</button>
      </div>
    </div>

    <div v-else class="card">
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
const loginBusy = ref(false)
const passwordNeeded = ref(false)
const loginForm = ref({ phone: '', code: '', password: '' })
async function load() { try { status.value = await api.getStatus() } catch {} }
async function loadTelegramAuth() {
  try {
    const auth = await api.getTelegramAuthStatus()
    if (auth.phone && !loginForm.value.phone) loginForm.value.phone = auth.phone
  } catch {}
}
async function sendCode() {
  if (!loginForm.value.phone) return toast('请输入手机号', 'error')
  loginBusy.value = true
  try { await api.sendTelegramCode({ phone: loginForm.value.phone }); toast('验证码已发送') }
  catch (e) { toast(e.message, 'error') } finally { loginBusy.value = false }
}
async function signIn() {
  if (!loginForm.value.code) return toast('请输入验证码', 'error')
  loginBusy.value = true
  try {
    const res = await api.signInTelegram({ code: loginForm.value.code })
    if (res.status === 'password_needed') { passwordNeeded.value = true; toast('需要输入二步密码'); return }
    toast('Telegram 登录成功'); await load()
  } catch (e) { toast(e.message, 'error') } finally { loginBusy.value = false }
}
async function submitPassword() {
  if (!loginForm.value.password) return toast('请输入二步密码', 'error')
  loginBusy.value = true
  try { await api.signInTelegramPassword({ password: loginForm.value.password }); toast('Telegram 登录成功'); passwordNeeded.value = false; await load() }
  catch (e) { toast(e.message, 'error') } finally { loginBusy.value = false }
}
async function send() {
  if (!sendForm.value.chat_id || !sendForm.value.text) return
  sending.value = true
  try { await api.sendMessage({ chat_id: Number(sendForm.value.chat_id), text: sendForm.value.text }); toast('消息已发送'); sendForm.value.text = '' }
  catch (e) { toast(e.message, 'error') } finally { sending.value = false }
}
onMounted(async () => { await load(); await loadTelegramAuth() })
</script>
