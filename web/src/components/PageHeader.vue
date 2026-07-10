<template>
  <div class="flex flex-wrap items-end justify-between gap-3 mb-6">
    <div class="min-w-0">
      <h2 class="text-xl font-bold tracking-tight">{{ title }}</h2>
      <p v-if="description" class="text-[13px] text-dim mt-1">{{ description }}</p>
    </div>
    <div v-if="$slots.default" class="flex flex-wrap items-center gap-2">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>
