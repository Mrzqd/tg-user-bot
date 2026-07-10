<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="relative inline-flex w-9 h-5 shrink-0 rounded-full border-none cursor-pointer outline-none transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-accent/40 disabled:opacity-40 disabled:cursor-not-allowed"
    :class="modelValue ? 'bg-accent' : 'bg-border-strong'"
    @click="$emit('update:modelValue', !modelValue)"
  >
    <span
      class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-md transition-transform duration-200"
      :class="modelValue ? 'translate-x-4' : ''"
    ></span>
  </button>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])
</script>
