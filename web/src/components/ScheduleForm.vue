<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
    <FormField label="Chat ID">
      <input class="input-base" :value="modelValue.chat_id" placeholder="-1001234567890" @input="upd('chat_id', $event.target.value)" />
    </FormField>

    <FormField label="话题 ID" hint="0 表示默认话题">
      <input class="input-base" type="number" :value="modelValue.topic_id" placeholder="0" @input="upd('topic_id', Number($event.target.value) || 0)" />
    </FormField>

    <FormField label="任务类型" class="sm:col-span-2">
      <select class="input-base" :value="modelValue.type" @change="upd('type', $event.target.value)">
        <option value="cron">周期（Cron）</option>
        <option value="once">单次 — 绝对时间</option>
        <option value="delay">单次 — 相对延时</option>
      </select>
    </FormField>

    <FormField v-if="modelValue.type === 'cron'" label="Cron 表达式" class="sm:col-span-2">
      <input class="input-base" :value="modelValue.cron_expr" placeholder="30 9 * * *" @input="upd('cron_expr', $event.target.value)" />
      <template #hint>
        分 时 日 月 星期 — 例：<code class="text-accent-light">30 9 * * 1-5</code> = 工作日 9:30
      </template>
    </FormField>

    <FormField v-else-if="modelValue.type === 'once'" label="执行时间（北京时间）" class="sm:col-span-2">
      <input class="input-base" type="datetime-local" :value="modelValue.run_at" @input="upd('run_at', $event.target.value)" />
    </FormField>

    <FormField v-else label="延时" class="sm:col-span-2">
      <input class="input-base" :value="modelValue.delay" placeholder="1d5h30m" @input="upd('delay', $event.target.value)" />
      <template #hint>
        d=天 h=时 m=分 s=秒，可组合 — 例：<code class="text-accent-light">1h30m</code>、<code class="text-accent-light">2d</code>、<code class="text-accent-light">30s</code>
      </template>
    </FormField>

    <FormField label="消息内容" class="sm:col-span-2">
      <textarea
        class="input-base !h-auto py-2 resize-y"
        rows="2"
        :value="modelValue.text"
        placeholder="输入要发送的消息内容"
        @input="upd('text', $event.target.value)"
      ></textarea>
    </FormField>

    <FormField label="自动删除（秒）" hint="0 表示不删除">
      <input class="input-base" type="number" :value="modelValue.delete_after" placeholder="0" @input="upd('delete_after', Number($event.target.value) || 0)" />
    </FormField>
  </div>
</template>

<script setup>
import FormField from './FormField.vue'

const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])

function upd(key, val) {
  emit('update:modelValue', { ...props.modelValue, [key]: val })
}
</script>
