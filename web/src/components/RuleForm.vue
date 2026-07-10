<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
    <FormField label="关键词">
      <input class="input-base" :value="modelValue.keyword" placeholder="你好" @input="upd('keyword', $event.target.value)" />
    </FormField>

    <FormField label="动作">
      <select class="input-base" :value="modelValue.action" @change="upd('action', $event.target.value)">
        <option value="reply">文字回复</option>
        <option value="click_button">点击按钮</option>
      </select>
    </FormField>

    <FormField
      :label="isClick ? '回复内容（可选，点击后额外发送）' : '回复内容'"
      :class="isClick ? '' : 'sm:col-span-2'"
    >
      <input
        class="input-base"
        :value="modelValue.reply_text"
        :placeholder="isClick ? '留空则只点击按钮' : '欢迎！'"
        @input="upd('reply_text', $event.target.value)"
      />
      <template #hint>
        正则可用 <code class="text-accent-light">$1</code> <code class="text-accent-light">$2</code> 引用捕获组；条件模板 <code class="text-accent-light">{if 条件}A{else}B{endif}</code>
      </template>
    </FormField>

    <FormField v-if="isClick" label="按钮匹配" hint="按钮文字或索引（0、1、2…），留空点击第一个">
      <input class="input-base" :value="modelValue.click_text" placeholder="留空=第一个" @input="upd('click_text', $event.target.value)" />
    </FormField>

    <FormField label="Chat ID" hint="0 表示对全部监控群组生效">
      <input class="input-base" :value="modelValue.chat_id" placeholder="0" @input="upd('chat_id', $event.target.value)" />
    </FormField>

    <FormField label="话题 ID" hint="0 表示全部话题">
      <input class="input-base" type="number" :value="modelValue.topic_id" placeholder="0" @input="upd('topic_id', Number($event.target.value) || 0)" />
    </FormField>

    <FormField label="触发条件（留空 = 始终触发）" class="sm:col-span-2">
      <input class="input-base" :value="modelValue.condition" placeholder='例: sender_id != 123 and text contains "VIP"' @input="upd('condition', $event.target.value)" />
      <template #hint>
        变量 <code class="text-accent-light">sender_id</code> <code class="text-accent-light">sender_name</code> <code class="text-accent-light">text</code> <code class="text-accent-light">$1</code> <code class="text-accent-light">msg_len</code> <code class="text-accent-light">has_buttons</code>；
        操作 <code class="text-accent-light">==</code> <code class="text-accent-light">!=</code> <code class="text-accent-light">contains</code> <code class="text-accent-light">and</code> <code class="text-accent-light">or</code>
      </template>
    </FormField>

    <FormField label="回复延迟（秒）" hint="0 表示立即回复">
      <input class="input-base" type="number" :value="modelValue.reply_delay" placeholder="0" @input="upd('reply_delay', Number($event.target.value) || 0)" />
    </FormField>

    <FormField label="自动删除（秒）" hint="0 表示不删除">
      <input class="input-base" type="number" :value="modelValue.delete_after" placeholder="0" @input="upd('delete_after', Number($event.target.value) || 0)" />
    </FormField>

    <div class="sm:col-span-2 flex flex-wrap items-center gap-x-8 gap-y-3 pt-1">
      <div class="flex items-center gap-2.5">
        <ToggleSwitch :model-value="modelValue.is_regex" @update:model-value="v => upd('is_regex', v)" />
        <span class="text-[13px] text-dim">正则匹配</span>
      </div>
      <div class="flex items-center gap-2.5">
        <ToggleSwitch :model-value="modelValue.no_quote" @update:model-value="v => upd('no_quote', v)" />
        <span class="text-[13px] text-dim">直接发送（不引用原消息）</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import FormField from './FormField.vue'
import ToggleSwitch from './ToggleSwitch.vue'

const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])

const isClick = computed(() => props.modelValue.action === 'click_button')

function upd(key, val) {
  emit('update:modelValue', { ...props.modelValue, [key]: val })
}
</script>
