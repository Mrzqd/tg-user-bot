<template>
  <div class="flex flex-col gap-3">
    <div class="flex gap-3">
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">关键词</label>
        <input class="input-base" :value="modelValue.keyword" @input="upd('keyword', $event.target.value)" placeholder="你好" />
      </div>
      <div class="w-40 flex flex-col gap-1">
        <label class="text-xs text-dim">动作</label>
        <select class="input-base" :value="modelValue.action" @change="upd('action', $event.target.value)">
          <option value="reply">文字回复</option>
          <option value="click_button">点击按钮</option>
        </select>
      </div>
    </div>
    <div class="flex gap-3">
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">{{ modelValue.action === 'click_button' ? '回复内容（可选，点击后额外发送）' : '回复内容' }}</label>
        <input class="input-base" :value="modelValue.reply_text" @input="upd('reply_text', $event.target.value)" :placeholder="modelValue.action === 'click_button' ? '留空则只点击按钮' : '欢迎！'" />
        <span class="text-[11px] text-dim">正则 <code class="text-accent">$1</code> <code class="text-accent">$2</code> 引用捕获组；条件模板 <code class="text-accent">{if 条件}A{else}B{endif}</code></span>
      </div>
      <div v-if="modelValue.action === 'click_button'" class="w-44 flex flex-col gap-1">
        <label class="text-xs text-dim">按钮匹配</label>
        <input class="input-base" :value="modelValue.click_text" @input="upd('click_text', $event.target.value)" placeholder="留空=第一个" />
        <span class="text-[11px] text-dim">按钮文字或索引（0、1、2...）</span>
      </div>
    </div>
    <div class="flex gap-3">
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">Chat ID（0=全部群组）</label>
        <input class="input-base" :value="modelValue.chat_id" @input="upd('chat_id', $event.target.value)" placeholder="0" />
      </div>
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">话题 ID（0=全部话题）</label>
        <input class="input-base" type="number" :value="modelValue.topic_id" @input="upd('topic_id', Number($event.target.value) || 0)" placeholder="0" />
      </div>
    </div>
    <div class="flex flex-col gap-1">
      <label class="text-xs text-dim">触发条件（留空=始终触发）</label>
      <input class="input-base" :value="modelValue.condition" @input="upd('condition', $event.target.value)" placeholder='例: sender_id != 123 and text contains "VIP"' />
      <span class="text-[11px] text-dim">变量: <code class="text-accent">sender_id</code> <code class="text-accent">sender_name</code> <code class="text-accent">text</code> <code class="text-accent">$1</code> <code class="text-accent">msg_len</code> <code class="text-accent">has_buttons</code>　操作: <code class="text-accent">==</code> <code class="text-accent">!=</code> <code class="text-accent">contains</code> <code class="text-accent">and</code> <code class="text-accent">or</code></span>
    </div>
    <div class="flex gap-3">
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">延迟（秒，0=立即）</label>
        <input class="input-base" type="number" :value="modelValue.reply_delay" @input="upd('reply_delay', Number($event.target.value) || 0)" placeholder="0" />
      </div>
      <div class="flex-1 flex flex-col gap-1">
        <label class="text-xs text-dim">自动删除（秒，0=不删除）</label>
        <input class="input-base" type="number" :value="modelValue.delete_after" @input="upd('delete_after', Number($event.target.value) || 0)" placeholder="0" />
      </div>
    </div>
    <div class="flex gap-5">
      <label class="flex items-center gap-2 text-sm text-dim cursor-pointer">
        <input type="checkbox" :checked="modelValue.is_regex" @change="upd('is_regex', $event.target.checked)" class="accent-accent" /> 正则匹配
      </label>
      <label class="flex items-center gap-2 text-sm text-dim cursor-pointer">
        <input type="checkbox" :checked="modelValue.no_quote" @change="upd('no_quote', $event.target.checked)" class="accent-accent" /> 直接发送（不引用原消息）
      </label>
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
