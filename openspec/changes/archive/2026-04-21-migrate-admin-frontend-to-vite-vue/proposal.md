## Why

当前后台虽然已经拆成多页面，但仍然依赖 Flask 模板渲染，前端结构、交互组织和后续扩展能力都明显受限。现在需要把管理台前端迁移到基于 Vue + Vite 的独立工程，并复用 `/Users/haojiayu/Documents/me/github/v3-admin-vite-main` 的后台模板能力，为后续页面扩展、状态管理和组件化开发建立稳定基础。

## What Changes

- **BREAKING** 将当前 Flask 模板式后台页面迁移为基于 Vue 的单页管理台，生产环境改为由后端分发构建后的前端静态资源。
- 以 `/Users/haojiayu/Documents/me/github/v3-admin-vite-main` 为前端基础模板，在本项目内落地对应目录结构、布局模式、路由体系和组件组织方式。
- 沿用模板项目现有的技术栈版本，在本项目内按 `vite 7.3.1 + Vue 3` 的构建基线落地，并根据本项目需要裁剪无关演示页面与示例模块。
- 为平台配置、通知管理、账户管理、执行记录、系统设置和登录流程提供前端可调用的后台管理 API，而不是继续依赖服务器模板表单提交。
- 保留现有管理员会话认证、调度逻辑和数据模型，前端仅改为通过异步请求读取与提交数据。
- 支持本地开发时前后端分离运行，以及生产环境下由 Flask 对 SPA 路由做回退分发。

## Capabilities

### New Capabilities
- `admin-frontend-delivery`: 以模板项目同版本技术栈构建并交付后台管理单页应用，首期基线为 `vite 7.3.1 + Vue 3`，支持开发态和生产态集成。
- `admin-management-api`: 提供受管理员会话保护的后台 JSON API，覆盖登录会话、平台、通知、账户、执行记录和系统设置的前端读写需求。

### Modified Capabilities
- `admin-console-navigation`: 后台导航从服务器模板页面切换为 Vue 管理台内的前端路由与深链接访问模型。

## Impact

- 主要影响 [app.py](/Users/haojiayu/Documents/me/github/mtlogin-py/app.py) 的路由组织方式，需新增 `/api/admin/**` 接口和 SPA 静态资源分发逻辑。
- 现有 `templates/*.html` 管理页面将逐步退出主流程，只保留登录回退或完全由前端接管。
- 项目需要新增前端工程目录、`package.json`、Vite 配置、Vue 路由、状态管理和构建脚本，并参考 `/Users/haojiayu/Documents/me/github/v3-admin-vite-main` 完成迁移。
- 部署流程会新增 Node/pnpm 构建步骤，README 和开发说明需要同步更新。
