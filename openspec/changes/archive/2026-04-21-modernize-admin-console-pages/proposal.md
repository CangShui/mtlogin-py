## Why

当前后台所有管理能力都堆叠在单个 `dashboard` 页面里，信息密度高但层次混乱，随着平台、通知、账户和执行记录能力增加，页面已经难以扩展和快速定位。现在需要把后台重构为现代化的多页面管理台，减少单页负担，并补齐账户列表的关键运营字段，便于日常巡检和调度管理。

## What Changes

- 将现有单页后台重构为共享管理壳层下的多页面结构，至少拆分为平台配置、通知管理、执行记录查询、系统设置、账户管理等独立页面。
- 新增统一的后台导航、页面标题区、统计卡片和响应式布局，整体视觉升级为更现代的管理控制台风格。
- 为系统设置提供独立入口，承载现有管理员账户设置能力，避免继续与业务配置混排。
- 调整各管理能力的路由和模板组织方式，使列表区、筛选区、编辑区按页面职责拆分。
- 扩展账户管理列表，新增上传量、下载量、魔力值、最近一次登录成功时间、下次执行时间等字段展示。
- 保留现有数据模型、调度逻辑与 CRUD 能力，不在本变更中引入前后端分离或新的后端服务。

## Capabilities

### New Capabilities
- `admin-console-navigation`: 提供现代化后台壳层、统一导航和多页面访问入口。
- `system-settings-management`: 提供独立的系统设置页面来管理管理员账号等系统级配置。

### Modified Capabilities
- `platform-config-management`: 平台配置从单页区块改为独立页面，并接入统一后台导航。
- `notification-channel-management`: 通知管理从单页区块改为独立页面，并接入统一后台导航。
- `login-account-management`: 账户管理改为独立页面，并扩展列表字段展示最近执行摘要和下次执行时间。
- `execution-history-query`: 执行记录查询改为独立页面，并接入统一筛选与结果展示布局。

## Impact

- 主要影响 [app.py](/Users/haojiayu/Documents/me/github/mtlogin-py/app.py) 中的页面路由、模板渲染上下文和账户列表查询逻辑。
- 主要影响 [templates/dashboard.html](/Users/haojiayu/Documents/me/github/mtlogin-py/templates/dashboard.html) 的单页模板拆分，预计会新增多个页面模板与共享布局片段。
- 账户列表查询需要增加对最新执行指标和下一次计划执行时间的聚合或计算输出。
- README 与后台使用说明需要更新，反映新的页面结构和入口方式。
