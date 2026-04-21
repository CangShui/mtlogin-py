# MTLogin 管理后台

这个项目现在是一个带登录后台的 M-Team 管理服务。管理员登录后，会进入一个多页面管理控制台，可以分别管理平台配置、通知渠道、多个登录账户、执行记录和系统设置；后台会按账户级 cron 计划执行登录/刷新操作，也支持按账户手动立即执行。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 本地启动

```bash
python app.py
```

默认行为：

- 管理后台地址：`http://127.0.0.1:8000`
- 默认管理员账号：`admin`
- 默认管理员密码：`admin123456`
- 本地数据库：`./mtlogin.db`
- 本地日志：`./mtlogin.log`

首次登录后建议立即在后台修改管理员密码。

如果需要自定义启动参数：

```bash
python app.py \
  --host 0.0.0.0 \
  --port 8000 \
  --db-path ./mtlogin.db \
  --log-file ./mtlogin.log \
  --admin-username admin \
  --admin-password admin123456
```

## Docker 使用

构建镜像：

```bash
docker build -t mtlogin-py .
```

运行容器：

```bash
docker run --rm -p 8000:8000 mtlogin-py
```

如果你想在首次启动时指定管理员账号密码：

```bash
docker run --rm -p 8000:8000 \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD="change-me-now" \
  mtlogin-py
```

容器内会把日志和 SQLite 数据库写到 `/app/mtlogin.log`、`/app/mtlogin.db`，不需要映射宿主机。

## 后台功能

- 管理员账号密码登录
- 现代化多页面管理控制台
- 平台配置独立页面
- 通知管理独立页面
- 多个登录账户独立管理页面
- 账户绑定一个平台和多个通知渠道
- 账户列表展示上传量、下载量、魔力值、最近一次登录成功时间、下次执行时间
- 按账户手动立即执行
- 后台线程按账户级 cron 表达式定时执行
- 执行记录独立查询页面
- 系统设置独立页面，可修改管理员账号并查看最近日志

## 页面结构

登录成功后默认进入 `账户管理` 页面，同时后台提供统一导航：

- `账户管理`：维护账户配置、平台绑定、通知绑定，并查看最近执行摘要与下次执行时间
- `平台配置`：查看内置平台及启停状态
- `通知管理`：维护 Telegram 通知渠道
- `执行记录`：按条件筛选历史执行结果
- `系统设置`：修改管理员账号密码，并查看当前运行环境和最近日志

旧入口 `/dashboard` 仍然保留，但现在会重定向到 `账户管理` 页面。

## 后台配置说明

登录后台后可以管理这几类数据：

- `平台配置`
  - 当前内置 `mt` 平台
  - `API Host` 固定为 `api.m-team.io`
  - `API Referer` 固定为 `https://kp.m-team.cc/`
- `通知管理`
  - 当前仅支持 `tg` 渠道
  - 可配置 `Telegram Bot Token`、`Telegram Chat ID`、`Telegram 代理`
- `登录账户`
  - 每个账户可配置 `M-Team 用户名`、`M-Team 密码`、`TOTP 密钥`、`代理`、`Cron 表达式`
  - 可配置 `M-Team Auth Token`、`M-Team DID`、`超时秒数`、`Cookie 模式`、`跳过缓存`
  - 每个账户必须绑定一个已启用平台
  - 每个账户可勾选多个已启用通知渠道
  - 列表会显示最近一次执行的上传量、下载量、魔力值、最近一次登录成功时间，以及下次执行时间
- `执行记录`
  - 支持按账户、平台、状态、时间范围查询
  - 按最近执行时间倒序展示
- `系统设置`
  - 独立管理管理员账号密码
  - 查看当前服务监听地址、数据库路径、日志路径和最近日志

说明：

- 密码、TOTP、Auth Token、Telegram Token 这些敏感字段在页面里留空时，不会覆盖已有值。
- 配置保存后，后台调度线程会自动重新加载计划。
- “立即执行”现在是账户级操作，会将结果写入执行记录。
- 升级到新版本后，如果数据库里存在旧的单任务配置，系统会自动迁移出默认账户和默认 TG 通知渠道。

## 常见 Cron 示例

```bash
# 每 2 小时的第 2 分钟执行一次
2 */2 * * *

# 每天凌晨 3:30 执行一次
30 3 * * *

# 每 15 分钟执行一次
*/15 * * * *
```

## 环境变量

`app.py` 启动时支持这些环境变量：

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `HOST` | `0.0.0.0` | Web 服务监听地址 |
| `PORT` | `8000` | Web 服务端口 |
| `DB_PATH` | `./mtlogin.db` | SQLite 数据库路径 |
| `LOG_FILE` | `./mtlogin.log` | 日志文件路径 |
| `ADMIN_USERNAME` | `admin` | 初始管理员用户名 |
| `ADMIN_PASSWORD` | `admin123456` | 初始管理员密码，仅首次初始化时使用 |
| `SECRET_KEY` | 随机生成 | Flask Session 密钥 |

M-Team 相关参数仍然支持通过环境变量提供初始默认值，后台未保存配置时会使用这些默认值：

- `USERNAME`
- `PASSWORD`
- `TOTPSECRET`
- `CRONTAB`
- `PROXY`
- `M_TEAM_AUTH`
- `M_TEAM_DID`
- `API_HOST`
- `API_REFERER`
- `TGBOT_TOKEN`
- `TGBOT_CHAT_ID`
- `TGBOT_PROXY`
- `TIME_OUT`
- `COOKIE_MODE`

## 兼容的脚本模式

原来的 `mtlogin.py` 仍然保留，可以继续单独作为脚本运行：

```bash
python mtlogin.py --username "站点用户名" --password "站点密码" --totpsecret "TOTP密钥"
```

也仍然支持：

- `--proxy`
- `--crontab`
- `--skip-cache`
- `--log-file`
- `--db-path`

## 安全说明

- 管理员密码以哈希形式保存在 SQLite 中。
- M-Team 密码和 TOTP 需要可逆使用，所以仍会明文保存在本地数据库里。
- HTTP 调试日志已对密码、OTP 和 Authorization 做脱敏，但仍建议限制数据库和日志文件权限。
