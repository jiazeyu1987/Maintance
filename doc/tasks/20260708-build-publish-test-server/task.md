# 20260708 构建发布到测试服务器

Status: completed

## 任务目标
- 使用本轮专用短路径临时发布 worktree 构建 IntRuoyi code-only 发布包。
- 将同一 releaseTag 发布到测试服务器 172.30.30.58。
- 验证测试服 operation、.env IMAGE_TAG、backend/frontend 镜像 tag、backend health 与 frontend HTTP 200。
- 本次仅授权测试服发布；不执行 mark-tested、正式服、备份服、备份、恢复或回滚。

## 上一任务检查
- 20260707-showroom-legacy-order-prod-release 已有最终状态“已完成”，本次已将 Current Status 校正为 completed，可开始新任务。

## 发布输入
- 维护仓：D:\ProjectPackage\Int\IntRuoyiMaintance，分支 int_main，目标提交 9d25b871ec5459ea746898345cc267181cf6f77d。
- 后端仓：D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro，分支 int_main，目标提交 aa62aaef666be5d7f0fd1c2dc9a2ffb1357aedf0。
- 前端仓：D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3，分支 int_main，目标提交 4e72522b16fadd2d2c54b138ab5a25e12b7146e7。
- 发布范围：code-only，构建与测试服发布必须使用 SkipDatabaseSync 与 SkipMinioSync；但不跳过 migration / required SQL / manifest 门禁。

## 经验门禁
- 发布必须使用本轮专用临时 worktree，禁止直接从主工作区构建、验证或发布；主工作区未提交/未跟踪内容不得进入发布包。
- 临时 worktree 路径必须短而稳定，优先使用 D:\ProjectPackage\Int\IntRuoyiWorktrees\r<日期><标识>\m|b|f。
- 构建前必须记录三仓目标提交、分支与 dirty 状态，并检查 runtime-control 指向本轮临时 worktree。
- build-release 成功后必须校验发布包 manifest.json：releaseTag、publishScope、sourceRepos branch/commit/dirty=false 与本轮计划一致。
- 测试服发布预览必须核对 ServerHost=172.30.30.58、RemoteAppDir=/opt/intruoyi/runtime，不得出现正式服或备份服参数。
- 测试服完成必须同时验证 operation=SUCCESS、远端 .env IMAGE_TAG、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP=200。
- PowerShell/中文/远端命令必须显式 UTF-8；PowerShell 5.1 不使用 &&。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；使用干净临时发布 worktree 与 manifest/运行态门禁确认真实发布输入和输出。
- 是否存在临时补丁或绕过：否。

## BDD 场景
- BDD: code-only 测试服发布 -> Given 三仓目标提交已固定且主工作区存在不相关未提交内容 / When 在专用干净临时发布 worktree 执行 build-release 与 publish-test / Then 发布包 manifest 必须 dirty=false，测试服必须运行同一 releaseTag。

## 里程碑
1. M1：建立任务文档、历史任务状态校正与经验前置门禁。COMPLETED
2. M2：确认三仓目标提交并创建本轮短路径临时发布 worktree。COMPLETED
3. M3：执行构建前置门禁与 build-release，并校验 manifest。COMPLETED
4. M4：publish-test 到测试服务器并验证运行态。COMPLETED
5. M5：恢复运行控制台主路径、清理临时 worktree、回写日志并提交本任务产物。COMPLETED

## 预期验证
- GREEN: experience-preflight -> PASS 已记录后才执行真实发布动作。
- build operation SUCCESS，manifest publishScope=code-only 且 sourceRepos.dirty=false。
- publish-test operation SUCCESS，测试服 .env IMAGE_TAG、backend/frontend 镜像 tag、backend health 与 frontend HTTP 200 均匹配本轮 releaseTag。
- 临时发布 worktree 已删除或明确阻塞原因；运行控制台配置已恢复主路径。

## 当前状态
- 状态：已完成。
- 已完成：任务文档初始化、上一任务状态校正、三仓目标提交记录、经验门禁摘录、短路径临时发布 worktree 创建与验证、构建前置门禁、build-release 与 manifest 校验、publish-test 与测试服运行态验证。
- releaseTag：20260708_082248。
- 临时 worktree：D:\ProjectPackage\Int\IntRuoyiWorktrees\r260708test。
- 阻塞：无。

## 完成结果
- 状态：completed
- releaseTag：20260708_082248
- build-release operation：op-2026-07-08T002247940620100Z-0f904898-a2ab-49c8-a8b5-3c8351191d78
- publish-test operation：op-2026-07-08T003601417252800Z-cec73968-b79f-44fc-ae57-b6c765d9e182
- 测试服验证：.env IMAGE_TAG、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200 均通过。
- 范围限制：未执行 mark-tested、正式服、备份服、备份、恢复或回滚。
- 收尾：运行控制台配置已恢复主路径，临时发布 worktree 已删除。