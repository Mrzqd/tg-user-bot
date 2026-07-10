<template>
  <div class="relative min-h-screen flex items-center justify-center p-6 overflow-hidden">
    <!-- 背景装饰 -->
    <div class="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-accent/10 blur-3xl pointer-events-none"></div>
    <div class="absolute -bottom-40 -left-32 w-96 h-96 rounded-full bg-violet/10 blur-3xl pointer-events-none"></div>

    <div class="relative w-full max-w-sm">
      <div class="flex flex-col items-center mb-7">
        <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent to-violet flex items-center justify-center text-white shadow-xl shadow-accent/30 mb-4">
          <Icon name="send" :size="26" />
        </div>
        <h1 class="text-xl font-bold tracking-tight">TG Userbot</h1>
        <p class="text-[13px] text-dim mt-1">登录 Web 控制台以继续</p>
      </div>

      <div class="card !p-6 shadow-2xl shadow-black/40">
        <div class="flex flex-col gap-4">
          <FormField label="用户名">
            <input v-model="form.username" class="input-base" autocomplete="username" @keydown.enter="submit" />
          </FormField>

          <FormField label="密码">
            <input
              v-model="form.password"
              class="input-base"
              type="password"
              autocomplete="current-password"
              @keydown.enter="submit"
            />
          </FormField>

          <div v-if="turnstileRequired" ref="turnstileEl" class="min-h-16"></div>

          <div
            v-if="error"
            class="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-err/10 border border-err/30 text-[13px] text-err"
          >
            <Icon name="alert-circle" :size="15" class="mt-0.5" />
            <span class="break-all">{{ error }}</span>
          </div>

          <button class="btn-primary w-full" :disabled="loading" @click="submit">
            <Icon v-if="loading" name="loader" :size="14" class="animate-spin" />
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { api, setAccessToken } from '../api.js'
import Icon from '../components/Icon.vue'
import FormField from '../components/FormField.vue'

const emit = defineEmits(['logged-in'])
const loading = ref(false)
const error = ref('')
const turnstileEl = ref(null)
const turnstileSiteKey = ref('')
const turnstileRequired = ref(false)
const turnstileToken = ref('')
const turnstileWidgetId = ref(null)
const form = reactive({ username: 'admin', password: '' })

function loadTurnstileScript() {
  return new Promise((resolve, reject) => {
    if (window.turnstile) return resolve()
    const existing = document.querySelector('script[data-turnstile]')
    if (existing) {
      existing.addEventListener('load', resolve)
      existing.addEventListener('error', reject)
      return
    }
    const script = document.createElement('script')
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
    script.async = true
    script.defer = true
    script.dataset.turnstile = '1'
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

async function renderTurnstile() {
  if (!turnstileRequired.value || !turnstileSiteKey.value) return
  await loadTurnstileScript()
  await nextTick()
  turnstileWidgetId.value = window.turnstile.render(turnstileEl.value, {
    sitekey: turnstileSiteKey.value,
    theme: 'dark',
    callback: token => { turnstileToken.value = token },
    'expired-callback': () => { turnstileToken.value = '' },
  })
}

async function submit() {
  if (loading.value) return
  error.value = ''
  loading.value = true
  try {
    const res = await api.login({
      username: form.username,
      password: form.password,
      turnstile_token: turnstileToken.value,
    })
    setAccessToken(res.access_token)
    emit('logged-in')
  } catch (e) {
    error.value = e.message
    if (window.turnstile && turnstileWidgetId.value !== null) window.turnstile.reset(turnstileWidgetId.value)
    turnstileToken.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const config = await api.getAuthConfig()
    turnstileSiteKey.value = config.turnstile_site_key
    turnstileRequired.value = config.turnstile_required
    await renderTurnstile()
  } catch {
    error.value = '无法获取登录配置，请确认服务已启动'
  }
})
</script>
