<template>
  <label class="flex flex-col gap-1.5 min-w-0">
    <span class="text-xs font-medium text-dim">{{ label }}</span>
    <slot />
    <span v-if="hint || $slots.hint" class="text-[11px] text-faint leading-relaxed">
      <slot name="hint">{{ hint }}</slot>
    </span>
  </label>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  hint: { type: String, default: '' },
})
</script>
