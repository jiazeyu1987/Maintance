# 任务：DCC 批量识别覆盖策略测试服发布验证

Status: completed

## 任务目标

将 DCC 批量识别新增覆盖策略发布到测试服，并通过测试服真实页面验证按钮策略行为可用。本次只授权测试服，不操作正式服或备份服。

## 发布输入

- 后端目标提交：`991a4c9264`（任务: 增加DCC批量识别覆盖策略）
- 前端目标提交：`093cc1a9d`（任务: 增加DCC批量识别覆盖策略）
- 维护仓目标：当前已提交发布控制台能力，仅用于发布执行
- 发布范围：code-only，使用 `SkipDatabaseSync` 与 `SkipMinioSync`；但仍执行 migration / required SQL / manifest 门禁

## 经验门禁

- 每次发布必须使用本次专用临时发布 worktree，发布输入固定为目标提交对应的 Git 已提交内容，dirty 或未跟踪内容不得进入发布包。
- 测试服发布必须使用单一 releaseTag 完成 `build-release -> publish-test -> 测试服运行态验证`，不得拼接旧 releaseTag 证据。
- 构建前必须跑 migration policy gate 与发布脚本契约测试；code-only 不代表跳过 SQL / migration / manifest 门禁。
- 构建成功后必须读取发布包 `manifest.json`，核对 releaseTag、backend/frontend commit、sourceRepos dirty=false。
- 测试服验证必须同时核 operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200。
- 本次只授权测试服；禁止执行 mark-tested、promote-prod、promote-backup。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，本次只发布已完成并已提交的 DCC 覆盖策略实现。
- 是否存在临时补丁或绕过：否。

## 里程碑

1. M1：建立发布任务记录并完成经验前置门禁。
2. M2：创建后端、前端、维护仓临时发布 worktree 并检出目标提交。
3. M3：执行构建前置测试与发布包构建。
4. M4：发布到测试服并验证运行态。
5. M5：通过测试服真实页面验证 DCC 策略行为，记录结果。

## 预期验证

- 后端 DCC 测试与 SQL 发布门禁通过。
- 前端 DCC 静态测试与 lint 通过。
- release manifest 与目标提交一致且 dirty=false。
- 测试服运行态切换到本次 releaseTag。
- 真实页面中按钮策略可选择“跳过已有记录 / 跳过成功，重试失败和未识别 / 覆盖全部已有值”。

## Current Status

completed

已完成：releaseTag elease-20260706-1305-dcc-policy-test-v3 已部署到测试服，后端/前端容器、.env IMAGE_TAG、后端健康检查、前端 HTTP 200 和 DCC 批量识别覆盖策略弹窗真实页面验证均通过。

## 完成结果

- 发布包：elease-20260706-1305-dcc-policy-test-v3。
- 测试服运行态：backend/frontend 镜像均为 elease-20260706-1305-dcc-policy-test-v3，/actuator/health 返回 UP，前端首页 HTTP 200。
- SQL 修复：修复 20260705_showroom_legacy_product_code_name_backfill.sql 中 6 行产品名称续行未注释问题，并补充裸文本行回归测试。
- 页面验证：测试服真实登录 测试租户/aoteman，进入 /dcc/controlled-file/browser，选中 DCC E2E Documents，确认弹窗展示三种覆盖策略且默认选中 跳过已有记录。
- 范围限制：未执行 mark-tested、未推进正式服或备份服。
