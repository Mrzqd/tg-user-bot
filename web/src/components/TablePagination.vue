<template>
  <div class="flex items-center justify-center gap-1 mt-4">
    <button class="btn-icon" :disabled="page <= 0" title="上一页" @click="$emit('change', page - 1)">
      <Icon name="chevron-left" :size="16" />
    </button>
    <span class="text-xs text-dim px-2 tabular-nums">第 {{ page + 1 }} 页</span>
    <button class="btn-icon" :disabled="!hasMore" title="下一页" @click="$emit('change', page + 1)">
      <Icon name="chevron-right" :size="16" />
    </button>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'

defineProps({
  page: { type: Number, required: true },
  hasMore: { type: Boolean, default: false },
})
defineEmits(['change'])
</script>
