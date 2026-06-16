# 运行控制台前端视觉优化

## Task Goal

在不改变运行控制台接口契约和运维动作语义的前提下，提升独立控制台前端观感、信息层级和可扫描性。页面应保持本机运维工具气质：安静、紧凑、清楚、可信，不做营销式大屏或装饰型首页。

## Milestones

- [x] 创建任务文档，记录 BDD/TDD、经验门禁与设计约束。
- [x] 增加前端设计契约测试，先观察失败。
- [x] 优化 `frontend/src/App.vue` 的布局、状态条、表单、表格和视觉 token。
- [x] 运行静态契约、类型检查、构建与浏览器 E2E 视觉验收。
- [x] 更新任务记录并提交本任务改动。

## Expected Verification

- `python -X utf8 scripts\verify_contracts.py` 通过，包含新的前端设计契约。
- `pnpm --dir frontend typecheck` 通过。
- `pnpm --dir frontend build` 通过。
- Playwright 打开 `http://127.0.0.1:48181/` 或 Vite 预览地址，页面显示运行控制台，操作区、状态表、操作记录更清楚，浏览器 console error 为 0。

## 经验门禁

- 必须遵循 `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`：白色工作面、灰蓝边框、蓝色主操作、紧凑圆角、表格优先、工具栏和表格连贯。
- 本任务仅做独立控制台本机前端视觉优化，不执行发布、备份、恢复、回滚、重启、远端清理或真实写入动作。
- 不增加登录、权限、菜单依赖；运行控制台按钮仍由后端 `actionEnabled/blockedReason` 和提交状态约束。
- 不引入未验证依赖；当前前端栈为 Vue 3 + Element Plus，不改成 React/Tailwind。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，基于现有 Vue/Element Plus 页面做结构化设计系统化优化，并用静态契约防止回退。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed

已完成前端视觉优化、静态契约、类型检查、构建、桌面/移动 Playwright 视觉验收与收尾清理预览；未触发发布、备份、恢复、回滚、重启或远端清理动作。
