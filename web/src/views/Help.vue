<template>
  <div class="fade-in max-w-4xl">
    <PageHeader title="命令帮助" description="所有命令在聊天框以 . 开头发送，仅自己可见" />

    <div v-for="group in commands" :key="group.title" class="card mb-4">
      <div class="flex items-center gap-2.5 mb-4">
        <div class="w-8 h-8 rounded-lg bg-accent/12 text-accent flex items-center justify-center shrink-0">
          <Icon name="terminal" :size="15" />
        </div>
        <h3 class="text-sm font-semibold">{{ group.title }}</h3>
      </div>

      <div v-for="cmd in group.items" :key="cmd.cmd" class="mb-4 last:mb-0 pl-1">
        <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <code class="text-xs bg-bg-input px-2 py-1 rounded-md font-mono text-accent-light whitespace-nowrap border border-border/60">{{ cmd.cmd }}</code>
          <span class="text-[13px] text-white/90">{{ cmd.desc }}</span>
        </div>
        <pre v-if="cmd.example" class="mt-2 px-3 py-2.5 rounded-lg bg-bg-sunken border border-border/60 text-xs font-mono text-dim whitespace-pre-wrap leading-relaxed overflow-x-auto">{{ cmd.example }}</pre>
        <div v-if="cmd.note" class="flex items-start gap-1.5 mt-1.5 text-xs text-faint">
          <Icon name="info" :size="13" class="mt-0.5 shrink-0" />
          <span>{{ cmd.note }}</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="flex items-center gap-2.5 mb-4">
        <div class="w-8 h-8 rounded-lg bg-warn/12 text-warn flex items-center justify-center shrink-0">
          <Icon name="info" :size="15" />
        </div>
        <h3 class="text-sm font-semibold">使用说明</h3>
      </div>
      <ul class="text-[13px] text-dim space-y-2 list-disc pl-5 leading-relaxed">
        <li>所有命令以 <code class="text-accent-light text-xs">.</code> 开头，只有你自己可以看到（发出的消息）</li>
        <li><code class="text-accent-light text-xs">/del N</code> 后缀表示自动删除：回复或定时消息在发送 N 秒后自动删除</li>
        <li>Cron 格式：<code class="text-accent-light text-xs">分 时 日 月 星期</code>，与标准 Unix cron 相同</li>
        <li>单次任务支持绝对时间 <code class="text-accent-light text-xs">YYYY-MM-DD HH:MM</code> 或相对延时 <code class="text-accent-light text-xs">1d5h30m</code></li>
        <li>定时任务的时间均为<strong class="text-white/90">北京时间（UTC+8）</strong></li>
        <li>论坛群（Forum）支持<strong class="text-white/90">话题</strong>：聊天命令会自动绑定发送所在话题，网页端可手动指定话题 ID</li>
        <li>话题 ID 为 <code class="text-accent-light text-xs">0</code> 表示不限话题（关键词规则）或默认话题（定时消息）</li>
        <li>管理命令可回复某人的消息使用，或在命令后附加对方的 user ID</li>
        <li>
          <strong class="text-white/90">条件语法</strong>（<code class="text-accent-light text-xs">/if</code> 和 <code class="text-accent-light text-xs">{if}</code> 通用）：
          变量 <code class="text-accent-light text-xs">sender_id</code> <code class="text-accent-light text-xs">sender_name</code> <code class="text-accent-light text-xs">text</code> <code class="text-accent-light text-xs">$1</code> <code class="text-accent-light text-xs">$2</code> <code class="text-accent-light text-xs">msg_len</code> <code class="text-accent-light text-xs">has_buttons</code>；
          比较 <code class="text-accent-light text-xs">==</code> <code class="text-accent-light text-xs">!=</code> <code class="text-accent-light text-xs">&gt;</code> <code class="text-accent-light text-xs">&lt;</code> <code class="text-accent-light text-xs">contains</code> <code class="text-accent-light text-xs">startswith</code> <code class="text-accent-light text-xs">in [a,b]</code>；
          逻辑 <code class="text-accent-light text-xs">and</code> <code class="text-accent-light text-xs">or</code> <code class="text-accent-light text-xs">not</code>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import Icon from '../components/Icon.vue'
import PageHeader from '../components/PageHeader.vue'

const commands = [
  {
    title: '通用',
    items: [
      { cmd: '.ping', desc: '测试机器人连通性，回复 Pong' },
      { cmd: '.status', desc: '查看状态：账号信息、群组/规则/任务数量' },
      { cmd: '.help', desc: '在聊天中显示所有可用命令' },
    ],
  },
  {
    title: '群组监控 — 管理哪些群被监控',
    items: [
      { cmd: '.monitor add', desc: '将当前群加入监控列表', example: '.monitor add', note: '在你想监控的群里发送此命令' },
      { cmd: '.monitor remove', desc: '取消监控当前群', example: '.monitor remove' },
      { cmd: '.monitor list', desc: '查看所有已监控群组及其 Chat ID' },
    ],
  },
  {
    title: '关键词规则 — 检测到关键词后自动回复',
    items: [
      { cmd: '.rule add <关键词> | <回复> [选项]', desc: '添加关键词规则，支持文字回复、点击按钮、条件判断', example: '基础回复:\n.rule add 你好 | 欢迎加入！\n.rule add 价格 | 当前价格 99 元 /del 30\n\n提取消息内容回复（正则+捕获组）:\n.rule add 口令: (.+) | $1 /delay 2\n.rule add 🔑 口令: (.+?) | $1 /delay 3 /nq\n\n条件判断（/if 条件表达式）:\n.rule add 通知 | 已收到 /if sender_id == 123456\n.rule add (.+) | VIP用户好 /if text contains "VIP"\n\n条件模板（回复内容中使用 {if}）:\n.rule add (.+) | {if $1 == "VIP"}尊享回复{else}普通回复{endif}\n\n点击按钮:\n.rule add 红包 | /click 领取\n\n$1 $2 引用正则捕获组\n/nq = 直接发送 /click = 点击按钮\n/if 条件 = 满足条件才触发', note: '选项: /del N /delay N /nq /click [按钮] /if 条件' },
      { cmd: '.rule del <id>', desc: '通过 ID 删除一条规则', example: '.rule del 3' },
      { cmd: '.rule list', desc: '查看所有关键词规则的状态、作用域和设置' },
    ],
  },
  {
    title: '定时消息 — 按时间自动发送消息（北京时间）',
    items: [
      { cmd: '.sched add <cron> | <内容> [/del N]', desc: '创建周期性定时消息，使用 cron 表达式', example: '.sched add 30 9 * * * | 大家早上好！\n.sched add 0 */2 * * * | 自动签到 /del 60\n.sched add 0 18 * * 1-5 | 下班啦！', note: 'Cron 格式：分 时 日 月 星期。在话题中发送会自动绑定该话题' },
      { cmd: '.sched once <时间> | <内容> [/del N]', desc: '创建一次性定时消息，支持绝对时间和相对延时', example: '绝对时间:\n.sched once 2026-03-15 10:00 | 会议开始！\n.sched once 2026-12-31 23:59 | 新年快乐！ /del 120\n\n相对延时:\n.sched once 1h30m | 稍后提醒\n.sched once 1d | 明天提醒 /del 60\n.sched once 30s | 马上提醒', note: '相对延时支持: d(天) h(时) m(分) s(秒)，可任意组合如 1d5h30m' },
      { cmd: '.sched del <id>', desc: '删除定时任务并取消计时器', example: '.sched del 5' },
      { cmd: '.sched list', desc: '查看所有定时任务的触发条件和上次发送时间' },
    ],
  },
  {
    title: '管理操作 — 群管理功能（需要管理员权限）',
    items: [
      { cmd: '.ban', desc: '封禁用户。回复消息或附加 user ID', example: '.ban\n.ban 123456789' },
      { cmd: '.unban', desc: '解封用户', example: '.unban 123456789' },
      { cmd: '.mute [分钟]', desc: '禁言用户。指定分钟数为临时禁言，不指定为永久', example: '.mute\n.mute 30\n.mute 123456789 60', note: '回复消息可直接操作该用户，或提供 user ID' },
      { cmd: '.unmute', desc: '解除禁言', example: '.unmute' },
      { cmd: '.kick', desc: '踢出用户（封禁后立即解封）', example: '.kick' },
    ],
  },
]
</script>
