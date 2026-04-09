# mtlogin.py 使用说明

一个用于 M-Team 账号保活/状态刷新的 Python 脚本。 基于项目https://github.com/scjtqs2/mtlogin 通过python重构

脚本会进行登录（或复用本地缓存 token），然后请求一组接口并尝试调用 `updateLastBrowse` 更新浏览状态；支持 Telegram/QQPush/Feishu/ntfy 通知。


## 安装依赖示例：

```bash
pip install -r requirements.txt
```
## 快速开始
```bash
python mtlogin.py  --username "站点用户名"   --password "站点密码"   --totpsecret "TOTP密钥"   --tgbot-token "00000000000:AAAAAAAAAAAAAAAAAAAAAAA"  --tgbot-chat-id "-1000000000000"  --log-file /var/log/mtlogin.log   --db-path /root/mtlogin.db --verbose-config
```

## 功能概览

- 支持账号密码 + TOTP 二次验证登录
- 支持直接使用 `M_TEAM_AUTH` + `M_TEAM_DID`
- 本地持久化缓存登录态（SQLite）
- 支持代理
- 支持失败通知与成功通知
- 支持详细 HTTP 调试日志

## 命令行参数

```bash
python mtlogin.py [options]
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `--username` | string | 空 | 登录用户名 |
| `--password` | string | 空 | 登录密码 |
| `--totpsecret` | string | 空 | TOTP 密钥（2FA） |
| `--m-team-auth` | string | 空 | 直接使用鉴权 token |
| `--m-team-did` | string | 空 | 设备 DID |
| `--proxy` | string | 空 | HTTP/HTTPS 代理地址 |
| `--api-host` | string | `api.m-team.io` | API 域名 |
| `--api-referer` | string | `https://kp.m-team.cc/` | Referer/Origin |
| `--tgbot-token` | string | 空 | Telegram Bot Token |
| `--tgbot-chat-id` | int | `0` | Telegram Chat ID |
| `--db-path` | string | `/data/cookie.db` | SQLite 数据库路径 |
| `--mindelay` | int | `0` | 随机延迟最小分钟 |
| `--maxdelay` | int | `0` | 随机延迟最大分钟 |
| `--use-local-config` | flag | `false` | 启用脚本内 `LOCAL_CONFIG_OVERRIDES` 覆盖 |
| `--verbose-config` | flag | `false` | 启动时打印关键配置（脱敏） |
| `--log-file` | string | 空 | 日志文件路径 |

## 环境变量

脚本支持环境变量配置（可与命令行混用，命令行优先）。

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `USERNAME` | 空 | 用户名 |
| `PASSWORD` | 空 | 密码 |
| `TOTPSECRET` | 空 | TOTP 密钥 |
| `PROXY` | 空 | 代理 |
| `CRONTAB` | `2 */2 * * *` | cron 表达式（当前主流程默认单次执行） |
| `QQPUSH` | 空 | QQ 推送目标 |
| `QQPUSH_TOKEN` | 空 | QQPush Token |
| `M_TEAM_AUTH` | 空 | 鉴权 token |
| `UA` | 见源码默认值 | User-Agent |
| `API_HOST` | `api.m-team.io` | API 域名 |
| `API_REFERER` | `https://kp.m-team.cc/` | Referer |
| `WXCORPID` | 空 | 企业微信配置 |
| `WXAGENTSECRET` | 空 | 企业微信配置 |
| `WXAGENTID` | `0` | 企业微信配置 |
| `WXUSERID` | `@all` | 企业微信配置 |
| `MINDELAY` | `0` | 随机延迟最小值（分钟） |
| `MAXDELAY` | `0` | 随机延迟最大值（分钟） |
| `TIME_OUT` | `60` | 请求超时秒数 |
| `DB_PATH` | `/data/cookie.db` | SQLite 数据库路径 |
| `VERSION` | `1.1.4` | 请求头版本字段 |
| `WEB_VERSION` | `1140` | 请求头 webversion 字段 |
| `M_TEAM_DID` | 空 | 设备 DID |
| `DING_TALK_ROBOT_WEBHOOK_TOKEN` | 空 | 钉钉配置（预留） |
| `DING_TALK_ROBOT_SECRET` | 空 | 钉钉配置（预留） |
| `DING_TALK_ROBOT_AT_MOBILES` | 空 | 钉钉配置（预留） |
| `TGBOT_TOKEN` | 空 | Telegram Bot Token |
| `TGBOT_CHAT_ID` | `0` | Telegram Chat ID |
| `TGBOT_PROXY` | 空 | Telegram 代理 |
| `FEISHU_WEBHOOKURL` | 空 | 飞书 Webhook |
| `FEISHU_SECRET` | 空 | 飞书签名密钥（当前未参与签名逻辑） |
| `NTFY_URL` | 空 | ntfy 服务地址 |
| `NTFY_TOPIC` | 空 | ntfy topic |
| `NTFY_USER` | 空 | ntfy basic auth 用户名 |
| `NTFY_PASSWORD` | 空 | ntfy basic auth 密码 |
| `NTFY_TOKEN` | 空 | ntfy bearer token |
| `COOKIE_MODE` | `normal` | `strict` 或失败次数较多时清理本地 token |

## 配置优先级

1. 源码中的 `LOCAL_CONFIG_OVERRIDES`（仅当 `--use-local-config` 开启时）
2. 环境变量
3. 命令行参数（同名项会覆盖前两者）

## 本地数据与缓存

脚本使用 SQLite 保存登录态，默认数据库路径：`/data/cookie.db`（可改为 `--db-path`）。

`kv` 表常见键值：

- `m-team-auth`：Authorization token
- `m-team-did`：设备 DID
- `m-team-visitorid`：visitorid

## 日志说明

- 控制台会输出每次 HTTP 请求与响应（包含请求头/响应体）
- 使用 `--log-file` 时会同时写入文件
- 如日志中包含敏感信息，请注意权限控制与脱敏

## 退出行为

当前 `main` 流程是“单次执行”：

1. 构建配置
2. 执行一次任务
3. 退出进程

如果你希望按 `CRONTAB` 持续运行，需要把主流程改为调用 `job.loop()`。

## 常见问题

### 1) 提示“检测到本地缓存 token/did，跳过登录”

说明数据库里已有缓存凭据，脚本会直接复用。

### 2) 提示“连接成功，但更新状态失败”

通常表示登录和鉴权成功，但 `updateLastBrowse` 接口返回了业务失败（例如频率限制或服务端策略变化）。

### 3) 如何清理缓存并强制重新登录

删除你配置的数据库文件（例如 `./mtlogin.db`）后重跑，或在失败策略触发时让脚本自动清理。

## 安全建议

- 不要把真实账号密码、TOTP 密钥、Bot Token 提交到 GitHub
- 建议通过环境变量注入敏感配置
- 建议将数据库文件和日志文件加入 `.gitignore`
