<template>
  <Teleport to="body">
    <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-200" @click.self="$emit('close')">
      <div class="bg-bg-card border border-border rounded-xl p-6 w-[480px] max-w-[90vw] max-h-[80vh] overflow-y-auto fade-in">
        <h3 class="text-base font-semibold mb-5">{{ title }}</h3>
        <slot />
        <div class="flex justify-end gap-2 mt-6">
          <button class="btn-ghost" @click="$emit('close')">取消</button>
          <button class="btn-primary" @click="$emit('confirm')">{{ confirmText }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({ title: { type: String, default: '' }, confirmText: { type: String, default: '保存' } })
defineEmits(['close', 'confirm'])
</script>
