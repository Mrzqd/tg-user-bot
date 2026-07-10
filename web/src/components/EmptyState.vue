<template>
  <div class="flex flex-col items-center justify-center py-16 px-6 text-center">
    <div class="w-12 h-12 rounded-2xl bg-bg-input/60 border border-border flex items-center justify-center text-faint mb-4">
      <Icon :name="icon" :size="22" />
    </div>
    <p class="text-sm font-medium text-dim">{{ title }}</p>
    <p v-if="hint" class="text-xs text-faint mt-1.5 max-w-70">{{ hint }}</p>
    <div v-if="$slots.default" class="mt-5">
      <slot />
    </div>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'

defineProps({
  icon: { type: String, default: 'inbox' },
  title: { type: String, required: true },
  hint: { type: String, default: '' },
})
</script>
