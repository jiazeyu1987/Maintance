# 20260823 修复 TrainingRulesReadonlyTab 并继续测试服发布

## Task Goal

修复当前 app `int_main` HEAD 中 0 字节的 `TrainingRulesReadonlyTab.vue`，以可审计的最小源代码修复和回归测试恢复前端构建能力；提交修复后重新冻结维护/app HEAD，在专用 clean release worktree 中构建并仅发布测试服务器 `172.30.30.58`。未提交改动不得进入构建产物，禁止正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`。

## Milestones

1. 读取 bug/frontend/BDD 门禁，冻结当前 app HEAD，创建 task-owned fix worktree，记录根因和 BDD。
2. 在修复前运行 RED 回归测试，证明空 SFC/构建合同失败。
3. 恢复正式组件实现，补充最小回归合同测试，运行 GREEN 与相关前端检查并提交修复。
4. 从修复提交和维护 HEAD 创建新的 release worktree，构建维护控制台与测试发布包，校验 manifest/版本/变更说明。
5. 仅执行 `publish-test`，验证 operation、远端 tag、镜像、容器、health、HTTP、真实页面和运行控制台。
6. 记录问题、沉淀经验，`ready_for_closeout` 后 cleanup preview/apply，清理本任务 worktree 并完成最终证据。

## Expected Verification

- 修复前 RED 能稳定暴露空 SFC 构建失败；修复后 GREEN 能通过组件合同和前端构建。
- 修复提交只包含当前 bug 的生产文件与对应测试/证据，不覆盖并发改动。
- 新 release worktree clean，manifest、artifact、版本号和变更说明绑定修复提交与维护 HEAD。
- 同一 releaseTag 的 `build-release -> publish-test` 成功；测试服真实运行态和运行控制台版本/变更说明全部通过。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；组件或构建合同不满足时直接失败。
- 是否从根因和长期维护角度解决：是；恢复被提交删除的正式组件内容，并以回归测试固定 SFC 完整性。
- 是否存在临时补丁或绕过：否；不在 dirty 主工作区修补、不复用旧包/tag、不跳过构建或页面门禁。

## 经验门禁

- Trigger：修复发布阻塞的前端组件后继续仅测试服发布。
- Preflight check：读取 bug/frontend/BDD 文档、经验索引和发布规则；冻结 app HEAD；独立 fix worktree；先 RED 后实现；修复提交后重新建立 release worktree。
- Blocker：缺少可复现 RED、测试 runner、正式组件来源、修复提交或构建/manifest/运行态证据时停止。
- Verification：`execution-log.md` 记录 BDD、RED、GREEN、commit、worktree、build/publish operation、manifest 和真实运行态证据。
- Forbidden action：禁止改测试迎合坏行为、复制 dirty 主工作区、选择旧提交发布、吞异常或跳过真实页面。
- Evidence：本任务 `task.md`、`execution-log.md`、`bug-regression-evidence.md`、`frontend-feature-evidence.md` 和 `verification-report.md`。

## Current Status

completed

## Milestone Status

- Milestone 1: completed；已冻结 app 基线 `a0025c9427` 并创建 fix worktree。
- Milestone 2: completed；空 SFC 的两项 RED 已稳定复现。
- Milestone 3: completed；修复、三项静态契约、`ts:check`、`build:test` 与提交 `4535936e0` 已通过。
- Milestone 4: completed；r260823f10 专用 clean worktree 构建成功，build operation SUCCESS；manifest、artifact、版本号和 changeSet 均绑定 app commit 4f1f847b63bd82bb53ffc0081d7eeecfb1f5c47f，dirty=false。
- Milestone 5: completed；同一 releaseTag r11 的 publish-test operation SUCCESS；测试服 .env、实际镜像、容器、health、HTTP、release-info、release lock、migration 和运行控制台版本/变更说明均通过。未执行 mark-tested、promote-prod、promote-backup。
- Milestone 6: completed；问题已记录并沉淀到既有经验文档，task-closeout preview/apply 通过，本任务 release worktree 已删除，稳定运行控制台已恢复，最终任务记录待单独提交。
