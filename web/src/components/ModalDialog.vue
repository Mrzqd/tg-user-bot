<template>
  <Teleport to="body">
    <div
      class="modal-backdrop fixed inset-0 z-200 flex items-center justify-center p-4 bg-black/65 backdrop-blur-sm"
      @click.self="$emit('close')"
    >
      <div
        class="modal-panel bg-bg-card border border-border rounded-2xl w-full max-h-[85vh] flex flex-col shadow-2xl shadow-black/60"
        :class="wide ? 'max-w-2xl' : 'max-w-lg'"
      >
        <div class="flex items-center justify-between pl-6 pr-4 pt-4 shrink-0">
          <h3 class="text-[15px] font-semibold">{{ title }}</h3>
          <button class="btn-icon" title="关闭" @click="$emit('close')">
            <Icon name="x" :size="16" />
          </button>
        </div>
        <div class="px-6 py-4 overflow-y-auto flex-1">
          <slot />
        </div>
        <div class="flex justify-end gap-2 px-6 pb-5 shrink-0">
          <button class="btn-ghost" @click="$emit('close')">取消</button>
          <button :class="danger ? 'btn-danger' : 'btn-primary'" :disabled="busy" @click="$emit('confirm')">
            <Icon v-if="busy" name="loader" :size="14" class="animate-spin" />
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import Icon from './Icon.vue'

defineProps({
  title: { type: String, default: '' },
  confirmText: { type: String, default: '保存' },
  danger: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  wide: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'confirm'])

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  document.body.style.overflow = 'hidden'
})
onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>
