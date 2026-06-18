<template>
  <div class="flex flex-col gap-3">
    <div class="flex gap-3">
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">Chat ID</label>
        <input class="input-base" :value="modelValue.chat_id" @input="upd('chat_id', $event.target.value)" placeholder="-1001234567890" />
      </div>
      <div class="w-32 flex flex-col gap-1">
        <label class="text-xs text-dim">话题 ID</label>
        <input class="input-base" type="number" :value="modelValue.topic_id" @input="upd('topic_id', Number($event.target.value) || 0)" placeholder="0" />
      </div>
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">类型</label>
        <select class="input-base" :value="modelValue.type" @change="upd('type', $event.target.value)">
          <option value="cron">周期（Cron）</option>
          <option value="once">单次 — 绝对时间</option>
          <option value="delay">单次 — 相对延时</option>
        </select>
      </div>
    </div>
    <div v-if="modelValue.type === 'cron'" class="flex flex-col gap-1">
      <label class="text-xs text-dim">Cron 表达式</label>
      <input class="input-base" :value="modelValue.cron_expr" @input="upd('cron_expr', $event.target.value)" placeholder="30 9 * * *" />
      <span class="text-[11px] text-dim">分 时 日 月 星期 — 例: <code class="text-accent">30 9 * * 1-5</code> = 工作日 9:30</span>
    </div>
    <div v-else-if="modelValue.type === 'once'" class="flex flex-col gap-1">
      <label class="text-xs text-dim">执行时间（北京时间）</label>
      <input class="input-base" type="datetime-local" :value="modelValue.run_at" @input="upd('run_at', $event.target.value)" />
    </div>
    <div v-else class="flex flex-col gap-1">
      <label class="text-xs text-dim">延时</label>
      <input class="input-base" :value="modelValue.delay" @input="upd('delay', $event.target.value)" placeholder="1d5h30m" />
      <span class="text-[11px] text-dim">d=天 h=时 m=分 s=秒，可组合 — 例: <code class="text-accent">1h30m</code>、<code class="text-accent">2d</code>、<code class="text-accent">30s</code></span>
    </div>
    <div class="flex gap-3">
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">消息内容</label>
        <input class="input-base" :value="modelValue.text" @input="upd('text', $event.target.value)" placeholder="输入消息内容" />
      </div>
      <div class="w-32 flex flex-col gap-1">
        <label class="text-xs text-dim">自动删除（秒）</label>
        <input class="input-base" type="number" :value="modelValue.delete_after" @input="upd('delete_after', Number($event.target.value) || 0)" placeholder="0" />
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])
function upd(key, val) {
  emit('update:modelValue', { ...props.modelValue, [key]: val })
}
</script>
