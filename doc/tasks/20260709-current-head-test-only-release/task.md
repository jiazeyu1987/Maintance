# 20260709 当前提交仅测试服发布

## 任务目标

仅基于发布开始时冻结到专用干净 worktree 的已提交代码，构建维护控制台和 IntRuoyi code-only 发布包，并且只发布到测试服务器。未提交改动、未跟踪文件和主工作区脏内容不得进入构建产物。

## 发布范围

- 目标环境：测试服 `172.30.30.58`。
- 禁止范围：正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`、业务数据库整库同步、MinIO/NAS 业务文件同步。
- 最终 releaseTag：`release-20260709-current-head-test-v9`。
- 发布包目录：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260709-current-head-test-v9`。

## 冻结构建来源

- 维护仓提交：`1fe4d64a6d4a8840aca061aca3c0c6d72a07d280`。
- 后端仓提交：`f1ef04912951ef15ae0d2881c974c964c182d76e`。
- 前端仓提交：`d33339bd7e29f705d12d92d8409d7bc37d314566`。
- 临时发布 worktree 根目录：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3`。
- 维护控制台构建目录：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3\m`。
- 后端构建输入：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3\b`。
- 前端构建输入：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3\f`。
- 冻结状态：后端、前端 worktree 均为 detached HEAD 且 clean；维护 worktree 仅产生运行时目录，未产生新提交。
- 发布基线规则：构建开始前冻结并记录 worktree 提交；冻结后的源分支新增提交不触发本轮重复构建。

## 经验门禁

- 发布必须从本轮专用短路径临时 worktree 执行，禁止从脏主工作区直接构建。
- `build-release` 必须显式指定组件 `intruoyi`，且 `manifest.json` 不得包含 Website 仓或 website/showroom 包目录。
- code-only 发布必须使用 `SkipDatabaseSync` 与 `SkipMinioSync`，但不得跳过 required SQL、schema、migration、manifest 和发布门禁。
- Manifest v1 `sourceRepos` 必须与冻结提交一致且 `dirty=false`；legacy `release-manifest.json` 按自身 schema 校验，不强加 Manifest v1 字段。
- 发布前必须校验版本号、变更说明、281 个产物的大小与 SHA256、required SQL 哈希。
- `publish-test` 预览必须只包含测试服动作，不得出现正式服、备份服、推广或测试标记动作。
- 测试服写入前必须记录 `GREEN: experience-preflight -> PASS`。
- 发布后必须独立核对 operation、`.env IMAGE_TAG`、实际镜像 tag、容器、健康检查、前端 HTTP、真实页面、数据库迁移、唯一索引、控制台版本和变更说明。
- Windows PowerShell 5.1 不使用 `&&`；中文文件显式 UTF-8；SSH `bash -s` 使用字节输入避免 CRLF。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；使用冻结 worktree、双清单分 schema 校验、数据库冲突前置修复和独立运行态验证。
- 是否存在临时补丁或绕过：否；测试服冲突数据按已授权正式业务规则事务修复，并保留备份、回滚演练与引用不变证据。

## BDD 场景

- BDD: 干净已提交代码构建 -> Given 三仓主工作区存在未提交或未跟踪内容 / When 从发布开始时冻结的 HEAD 创建专用干净 worktree 并构建 / Then Manifest v1 必须记录冻结提交且业务仓 `dirty=false`，未提交内容不得进入包。
- BDD: 仅测试服发布 -> Given v9 发布包来源、版本、变更说明和哈希均通过 / When 执行 `publish-test` / Then 只允许测试服务器动作，正式服、备份服、推广和测试标记动作必须为零。
- BDD: 真实运行态验收 -> Given publish operation 成功 / When 核对服务器、数据库和真实前端页面 / Then `.env`、实际镜像、容器、健康、HTTP、迁移、索引、控制台版本和变更说明必须全部通过。
- BDD: 已知控制台探测缺陷透明记录 -> Given Linux 容器内运维矩阵错误调用 `powershell.exe` / When 独立运行态检查全部通过 / Then 不得用矩阵错误结果替代真实验证，缺陷必须保持公开记录。

## 里程碑

1. M1：建立任务文档、读取经验门禁并记录 Git 基线。COMPLETED
2. M2：创建专用干净临时 worktree，并冻结三仓目标提交。COMPLETED
3. M3：构建维护控制台并从临时 worktree 启动本地运行控制台。COMPLETED
4. M4：构建 v9 测试发布包并校验 manifest、版本、变更说明和产物哈希。COMPLETED
5. M5：只发布测试服务器并完成服务器、数据库、HTTP 与 Playwright 真实页面验收。COMPLETED
6. M6：记录问题、沉淀前置经验、恢复本地主路径、清理临时 worktree并提交任务记录。COMPLETED

## 验证结果

- build-release operation：`op-2026-07-10T005259232612400Z-cb2a74e8-4ae2-4b97-a24a-ae0398d266b2`，`SUCCESS`。
- publish-test operation：`op-2026-07-10T011318297410400Z-dbee4822-c99c-40ff-894c-71f75679440a`，`SUCCESS`。
- Manifest v1：冻结后端/前端提交一致，`dirty=false`，组件 `intruoyi`，发布范围 `code-only`。
- 发布信息：版本 `release-20260709-current-head-test-v9`；变更说明 `Release package release-20260709-current-head-test-v9`。
- 产物：281/281 文件存在，大小与 SHA256 全部匹配。
- 远端 `.env IMAGE_TAG`：`release-20260709-current-head-test-v9`。
- 实际镜像：`intruoyi-backend:v9` 与 `intruoyi-frontend:v9` 对应完整 v9 tag，容器均为 running。
- 后端健康：HTTP 200 且 `{"status":"UP"}`。
- 前端：HTTP 200，HTML 非空；Playwright 真实登录并打开 `基础设施 -> 监控中心 -> 运行控制台`。
- 数据库：路由排程配置活跃冲突数 0；目标唯一索引列顺序正确；两项 required migration 和 test release lock 均为 APPLIED。
- 运行控制台：全局发布信息对话框显示 v9、变更说明、变更项及冻结的后端/前端提交。
- 环境边界：未操作正式服、备份服，未执行推广或 `mark-tested`。

## 已知问题

- `test-runtime-control-linux-powershell-status-probe`：测试服 Linux 后端内的运维矩阵调用 `powershell.exe`，矩阵显示 ERROR/unknown。实际镜像、容器、HTTP、数据库状态已独立验证通过。
- `test-runtime-control-release-status-current-tag-null`：测试服后端 `/release-status` 依赖失败的 overview，面板 current tag 为 null；全局发布信息对话框和本地维护控制台 API 正确显示 v9 与变更说明。
- 两项问题均已完整记录并沉淀为发布前置经验；本任务未修改产品代码，不将其静默隐藏或标记为正常。

## Cleanup Candidates

- `doc/tasks/20260709-current-head-test-only-release/evidence/`

## 当前状态

- 状态：已完成。
- Status: COMPLETED
- 发布结论：测试服发布验收通过，32/32 必需检查 PASS。
- 本地维护控制台：已停止发布 worktree Jar，使用同一冻结维护提交构建的 Jar 从主工作区路径启动；`http://127.0.0.1:48181/actuator/health` 为 `UP`。
- worktree 收口：本轮维护、后端、前端 worktree 未产生新提交；Git 注册和物理目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3` 均已删除。
- 清理预览：仅保留 `task.md` 与 `execution-log.md`，清理本任务 evidence 临时证据目录。
- 最终结果：构建、仅测试服发布、真实运行态、版本与变更说明、问题记录、经验沉淀和临时 worktree 清理全部完成。

## Current Status

completed
