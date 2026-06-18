# Telegram Userbot (MTProto)

基于 Telegram Client API (MTProto) 的生产级 Userbot，使用 Telethon + FastAPI + Vue 3 构建。

## 功能特性

- **群消息监听** - 实时监控指定群组的所有消息，自动记录日志
- **关键词自动回复** - 支持精确匹配和正则匹配，可按群组粒度配置
- **定时消息** - 支持一次性和 Cron 周期性定时发送
- **资源下载** - 回复媒体消息、Telegram 消息链接或媒体直链可下载图片 / 视频 / 文件等资源到本机目录
- **消息自动删除** - 自动回复和定时消息均支持配置发送后 N 秒自动删除
- **管理员操作** - Ban / Unban / Mute / Unmute / Kick 等群管功能
- **REST API** - 完整的 FastAPI 管理接口，支持远程控制
- **Web 管理面板** - Vue 3 构建的现代化暗色主题 Dashboard
- **代理支持** - SOCKS5 / SOCKS4 / HTTP 代理，支持用户名密码认证

## 架构

```
┌──────────────────────────────────────────────┐
│                main.py (Entry)               │
├──────────────────────┬───────────────────────┤
│   Telethon Client    │    FastAPI Server     │
│   (asyncio loop)     │    (uvicorn thread)   │
├──────────────────────┼───────────────────────┤
│   Event Handlers     │    REST API Routes    │
│   ├─ Listener        │    ├─ /api/groups     │
│   ├─ Commands (.xx)  │    ├─ /api/rules      │
│   └─ Admin           │    ├─ /api/schedules  │
│                      │    ├─ /api/messages    │
│   APScheduler        │    └─ /api/status     │
├──────────────────────┼───────────────────────┤
│                      │    Vue 3 SPA (/)      │
│                      │    Static from dist/  │
├──────────────────────┴───────────────────────┤
│           SQLAlchemy (async)                 │
│           SQLite / PostgreSQL                │
└──────────────────────────────────────────────┘
```

## 快速开始

### 1. 获取 Telegram API 凭证

前往 [https://my.telegram.org](https://my.telegram.org) 创建应用，获取 `API_ID` 和 `API_HASH`。

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的凭证
```

### 3. 安装依赖 & 构建前端

```bash
# Python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 前端
cd web && npm install && npm run build && cd ..
```

### 4. 启动

```bash
python main.py
```

首次启动会要求输入手机号和验证码完成登录，之后 session 文件会保存在 `sessions/` 目录。

### Docker 部署

```bash
docker-compose up -d
# 首次需要 attach 容器输入验证码
docker attach tg-userbot
```

## Web 管理面板

启动后访问 `http://localhost:8080` 即可进入 Web Dashboard。

Web 控制台使用 `.env` 中的 `WEB_USERNAME` / `WEB_PASSWORD` 登录；未设置 `WEB_PASSWORD` 时会临时回退使用 `API_SECRET_KEY`。如需启用 Cloudflare Turnstile，在 `.env` 配置 `TURNSTILE_SITE_KEY` 和 `TURNSTILE_SECRET_KEY`。

首次 Telegram 登录也在 Web 控制台完成：进入仪表盘后发送验证码、填写验证码；如果账号启用了二步验证，再填写二步密码。Docker 部署不再需要 attach 容器输入验证码。

面板功能：
- **Dashboard** - 状态总览 + 快速发消息
- **Groups** - 管理监控群组（添加 / 删除 / 暂停）
- **Rules** - 关键词自动回复规则管理
- **Schedules** - 定时消息管理（Cron 周期 / 一次性）
- **Logs** - 监控消息日志查询

前端开发模式：
```bash
cd web && npm run dev
# 访问 http://localhost:3000，API 自动代理到 :8080
```

## 聊天内命令

在任意聊天中发送以下命令（以 `.` 开头，仅自己可见）：

### 通用

| 命令 | 说明 |
|------|------|
| `.ping` | 测试连通性 |
| `.status` | 查看 Bot 状态 |
| `.help` | 显示帮助信息 |

### 资源下载

| 命令 | 说明 |
|------|------|
| `.download` / `.dl` | 回复媒体消息、Telegram 消息链接或媒体直链，下载资源到 `DOWNLOAD_DIR`（默认 `downloads/`） |

下载目标可在 Web 控制台的「系统设置」中切换为本地目录或 WebDAV。选择 WebDAV 后，文件会先下载到本地临时目录，再上传到远端目录，可配置上传后是否保留本地文件。

可在 `.env` 调整下载参数：

```env
DOWNLOAD_DIR=downloads
DOWNLOAD_THREADS=16
DOWNLOAD_PART_SIZE_KB=512
```

下载速度受 Telegram DC、代理、CPU 加解密和 MTProto 连接吞吐影响。项目依赖 `cryptg` 加速 Telethon 加解密；如线程数过高触发不稳定或限速，可将 `DOWNLOAD_THREADS` 调回 `8` 或 `4`。

WebDAV 上传单测：

```bash
python -m unittest discover -s test -p 'test_webdav_downloads.py' -v
```

WebDAV 真实冒烟测试（会上传一个小文本文件）：

```bash
WEBDAV_SMOKE_URL='http://your-host:5244/dav' \
WEBDAV_SMOKE_USERNAME='username' \
WEBDAV_SMOKE_PASSWORD='password' \
WEBDAV_SMOKE_REMOTE_PATH='/local/tg' \
python -m unittest discover -s test -p 'test_webdav_downloads.py' -k real_webdav -v
```

### 监控

| 命令 | 说明 |
|------|------|
| `.monitor add` | 将当前群加入监控 |
| `.monitor remove` | 取消监控当前群 |
| `.monitor list` | 列出所有监控群 |

### 关键词规则

| 命令 | 说明 |
|------|------|
| `.rule add <关键词> \| <回复> [/del N]` | 添加自动回复（N 秒后删除） |
| `.rule del <id>` | 删除规则 |
| `.rule list` | 列出所有规则 |

### 定时消息

| 命令 | 说明 |
|------|------|
| `.sched add <cron> \| <text> [/del N]` | 周期定时消息 |
| `.sched once <datetime> \| <text> [/del N]` | 一次性定时消息 |
| `.sched del <id>` | 删除定时任务 |
| `.sched list` | 列出所有定时任务 |

**示例：**
```
.sched add 30 9 * * 1-5 | Good morning!
.sched add 0 */2 * * * | Check-in /del 60
.sched once 2025-12-31 23:59 | Happy New Year! /del 120
```

### 管理员

| 命令 | 说明 |
|------|------|
| `.ban <reply/user_id>` | 封禁用户 |
| `.unban <reply/user_id>` | 解封用户 |
| `.mute <reply/user_id> [分钟]` | 禁言用户 |
| `.unmute <reply/user_id>` | 解除禁言 |
| `.kick <reply/user_id>` | 踢出用户 |

## REST API

所有接口需要 `X-API-Key` 请求头认证，Swagger 文档：`http://localhost:8080/docs`

## 代理配置

在 `.env` 中配置：

```env
TG_PROXY_TYPE=socks5
TG_PROXY_HOST=127.0.0.1
TG_PROXY_PORT=7890
TG_PROXY_USER=         # 可选
TG_PROXY_PASS=         # 可选
```

支持 `socks5`、`socks4`、`http` 三种代理类型。

## 项目结构

```
tg-user-bot/
├── main.py                 # 主入口
├── config.py               # 配置管理
├── requirements.txt        # Python 依赖
├── Dockerfile              # 多阶段构建 (Node + Python)
├── docker-compose.yml
├── bot/
│   ├── client.py           # Telethon 客户端封装 + 自动删除
│   ├── filters.py          # 关键词匹配过滤器
│   ├── scheduler.py        # APScheduler 定时任务
│   └── handlers/
│       ├── listener.py     # 消息监听 + 自动回复
│       ├── commands.py     # 自定义命令
│       └── admin.py        # 管理员操作
├── api/
│   ├── app.py              # FastAPI 应用 + 静态文件托管
│   ├── models.py           # Pydantic 模型
│   ├── deps.py             # API Key 认证
│   └── routes/
│       ├── groups.py       # 群组管理接口
│       ├── rules.py        # 关键词规则接口
│       ├── scheduler.py    # 定时任务接口
│       └── messages.py     # 消息发送 / 日志接口
├── database/
│   ├── engine.py           # 数据库引擎
│   ├── models.py           # SQLAlchemy 模型
│   └── crud.py             # CRUD 操作
├── utils/
│   └── logger.py           # Loguru 日志
└── web/                    # Vue 3 前端
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.vue
        ├── api.js          # API 客户端
        ├── router.js       # 路由
        ├── style.css       # 暗色主题样式
        ├── views/
        │   ├── Dashboard.vue
        │   ├── Groups.vue
        │   ├── Rules.vue
        │   ├── Schedules.vue
        │   └── Logs.vue
        └── components/
            ├── AppLayout.vue
            └── ModalDialog.vue
```

## 安全注意事项

- **Session 文件** (`sessions/*.session`) 等同于登录凭证，务必妥善保管
- **API Key** 请使用足够复杂的随机字符串
- 不要将 `.env` 和 session 文件提交到版本控制
- 建议使用独立的 Telegram 账号运行 Userbot
- Telegram 对自动化操作有频率限制，避免高频发送
- Web 面板建议在生产环境中配合反向代理 + HTTPS 使用

## 许可证

MIT License
