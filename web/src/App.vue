<template>
  <AppLayout>
    <router-view />
  </AppLayout>
  <div class="fixed top-5 right-5 z-300 flex flex-col gap-2">
    <div
      v-for="t in toasts" :key="t.id"
      class="px-4 py-2.5 rounded-lg text-sm text-white shadow-lg toast-anim"
      :class="t.type === 'error' ? 'bg-err' : 'bg-ok'"
    >{{ t.msg }}</div>
  </div>
</template>

<script setup>
import { ref, provide } from 'vue'
import AppLayout from './components/AppLayout.vue'

const toasts = ref([])
let toastId = 0

function toast(msg, type = 'success') {
  const id = ++toastId
  toasts.value.push({ id, msg, type })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, 3000)
}

provide('toast', toast)
</script>
