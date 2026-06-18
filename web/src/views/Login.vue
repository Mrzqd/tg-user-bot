<template>
  <div class="min-h-screen flex items-center justify-center p-6">
    <div class="card w-full max-w-md">
      <h1 class="text-xl font-semibold text-accent mb-1">TG Userbot</h1>
      <p class="text-sm text-dim mb-6">登录 Web 控制台</p>

      <div class="space-y-4">
        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">用户名</span>
          <input v-model="form.username" class="input-base" autocomplete="username" @keydown.enter="submit" />
        </label>

        <label class="block">
          <span class="text-xs text-dim mb-1.5 block">密码</span>
          <input v-model="form.password" class="input-base" type="password" autocomplete="current-password" @keydown.enter="submit" />
        </label>

        <div v-if="turnstileRequired" ref="turnstileEl" class="min-h-16"></div>

        <button class="btn-primary w-full justify-center" :disabled="loading" @click="submit">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { api, setAccessToken } from '../api.js'

const emit = defineEmits(['logged-in'])
const loading = ref(false)
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
    callback: token => { turnstileToken.value = token },
    'expired-callback': () => { turnstileToken.value = '' },
  })
}

async function submit() {
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
    alert(e.message)
    if (window.turnstile && turnstileWidgetId.value !== null) window.turnstile.reset(turnstileWidgetId.value)
    turnstileToken.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const config = await api.getAuthConfig()
  turnstileSiteKey.value = config.turnstile_site_key
  turnstileRequired.value = config.turnstile_required
  await renderTurnstile()
})
</script>
