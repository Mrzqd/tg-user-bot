<template>
  <Login v-if="!loggedIn" @logged-in="loggedIn = true" />
  <AppLayout v-else>
    <router-view />
  </AppLayout>

  <!-- 全局确认弹窗（替代原生 confirm） -->
  <ModalDialog
    v-if="confirmState"
    :title="confirmState.title"
    :confirm-text="confirmState.confirmText"
    :danger="confirmState.danger"
    @close="resolveConfirm(false)"
    @confirm="resolveConfirm(true)"
  >
    <p class="text-sm text-dim leading-relaxed">{{ confirmState.message }}</p>
  </ModalDialog>

  <!-- 全局通知 -->
  <div class="fixed top-5 right-5 z-300 flex flex-col items-end gap-2 pointer-events-none">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="flex items-center gap-2.5 pl-3.5 pr-4 py-2.5 rounded-xl text-sm text-white bg-bg-card border shadow-2xl shadow-black/50 pointer-events-auto"
        :class="t.type === 'error' ? 'border-err/40' : 'border-ok/40'"
      >
        <Icon
          :name="t.type === 'error' ? 'alert-circle' : 'check-circle'"
          :size="16"
          :class="t.type === 'error' ? 'text-err' : 'text-ok'"
        />
        <span>{{ t.msg }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref, provide } from 'vue'
import AppLayout from './components/AppLayout.vue'
import ModalDialog from './components/ModalDialog.vue'
import Icon from './components/Icon.vue'
import Login from './views/Login.vue'
import { getAccessToken } from './api.js'

const loggedIn = ref(Boolean(getAccessToken()))

// —— 通知 ——
const toasts = ref([])
let toastId = 0

function toast(msg, type = 'success') {
  const id = ++toastId
  toasts.value.push({ id, msg, type })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, 3200)
}

// —— 确认弹窗（Promise 风格） ——
const confirmState = ref(null)

function confirmAction(message, opts = {}) {
  return new Promise((resolve) => {
    confirmState.value = {
      message,
      title: opts.title || '确认操作',
      confirmText: opts.confirmText || '确认',
      danger: opts.danger !== false,
      resolve,
    }
  })
}

function resolveConfirm(result) {
  confirmState.value?.resolve(result)
  confirmState.value = null
}

provide('toast', toast)
provide('confirm', confirmAction)
</script>
