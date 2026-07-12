# 20260712 当前 HEAD 仅测试服发布

## Task Goal

基于本次发布启动时三仓当前分支最新已提交 HEAD 构建维护控制台和 IntRuoyi 测试发布包，仅发布到测试服务器；未提交改动不得进入构建产物，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 发布范围：仅测试服。
- 禁止动作：正式服发布、备份服发布、`mark-tested`、`promote-prod`、`promote-backup`。
- 构建来源：只能来自本任务开始时冻结的三仓 HEAD 已提交内容。

## Frozen Baseline

| Repo | Branch | Frozen HEAD | Main Workspace Status | Build Input |
| --- | --- | --- | --- | --- |
| maintenance | `int_main` | `481d03c1940f233ba12576801286ff2617e3a441` | dirty | 待创建干净临时发布 worktree |
| backend | `int_main` | `c7753b28997dbd8d8b3581250961646f00b14ccb` | dirty | `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p\b` |
| frontend | `int_main` | `2d10335f75a72f934aac52839fdb78a696036304` | dirty | `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p\f` |

## Milestones

- [x] 创建任务目录和最小任务文档。
- [x] 读取发布、worktree、PowerShell、服务器和经验索引门禁。
- [x] 创建本轮专用短路径临时发布 worktree 并检出冻结 HEAD。
- [x] 记录三仓 worktree 路径、构建目录、Git 状态和 clean 证明。
- [x] 构建维护控制台。
- [x] 执行 build-release 并校验发布包、Manifest v1、legacy manifest、版本号和变更说明。
- [x] 仅执行 publish-test。
- [x] 校验测试服真实运行态：operation、远端 `.env IMAGE_TAG`、镜像 tag、容器、health、HTTP、release-info、真实页面和运行控制台版本信息。
- [x] 记录全部问题并沉淀前置经验。
- [ ] 恢复本地运行控制台稳定路径，清理本任务临时 worktree，完成 closeout。

## Expected Verification

- 三仓发布 worktree 均为冻结提交且 `git status --porcelain` 为空。
- build-release operation 为 `SUCCESS`。
- 发布包 `manifest.json` 存在，sourceRepos 提交等于冻结提交且 dirty=false。
- 版本号和变更说明可追溯到本次 releaseTag / Manifest / release-info。
- publish-test operation 为 `SUCCESS`。
- 测试服真实运行态通过：`.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health=`UP`、frontend HTTP=200、`/release-info.json`、运行控制台版本与变更说明、Playwright 页面检查。
- 未执行正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`。
- 问题台账和前置经验已更新。

## 经验门禁

### 测试服发布主门禁

- Trigger: 仅测试服发布、当前 HEAD 发布、`publish-test`、运行态验收、运行控制台版本与变更说明验证。
- Preflight check: 创建任务目录；冻结三仓 HEAD 到本轮专用短路径 release worktree；构建前后校验 Manifest v1、legacy manifest、required SQL、publish-test preview 和测试服真实运行态。
- Blocker: 构建来源无法证明为冻结提交、manifest 缺失或 dirty、版本/变更说明无法确认、preview 非 test、operation 非 SUCCESS、镜像/health/HTTP/release-info/页面任一失败。
- Verification: 在 `execution-log.md` 记录冻结提交、worktree 路径、build/publish operation、manifest 校验、远端 `.env`、实际镜像、容器、health、HTTP、Playwright 页面和 worktree 清理结果。
- Forbidden action: 不得从脏主工作区构建；不得拼接不同 releaseTag；不得跳过真实页面验证；不得在 worktree 未清理或控制台仍指向临时路径时宣称完成；不得执行正式服/备份服/mark-tested/promote。
- Evidence: `docs/test-release-preflight.md`。

### 构建发布门禁

- Trigger: build-release、发布包、Manifest v1、required SQL、releaseTag、sourceRepos 校验。
- Preflight check: 构建预览必须包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；后端全量迁移 metadata policy gate 先通过；构建后读取发布包根目录 `manifest.json`。
- Blocker: sourceRepos commit 与冻结提交不一致、dirty=true、manifest 缺失、required SQL metadata 不合法、build operation 非 SUCCESS。
- Verification: 记录 build operation、manifest 路径、sourceRepos、artifact 校验、版本与变更说明来源。
- Forbidden action: 不得用 legacy `release-manifest.json` 或旧 Docker image 替代 Manifest v1 证据；不得复用失败 releaseTag 继续发布。
- Evidence: `docs/release-build-preflight-lessons.md`。

### PowerShell / SSH / Playwright 门禁

- Trigger: PowerShell 中文参数、多层 SSH/MySQL、release-info 中文、Playwright 页面验收。
- Preflight check: 设置 UTF-8 输入输出；复杂命令优先用标准输入或脚本文件；记录 `$LASTEXITCODE`；Playwright 先确认依赖与浏览器路径。
- Blocker: 命令输出编码不可读、SSH/JSON 输出无法证明真实状态、release-info 中文乱码且无其他权威证据、Playwright 无法真实打开页面。
- Verification: UTF-8 读取、退出码、远端命令输出、Playwright 截图/文本证据。
- Forbidden action: 不得把 PowerShell 默认编码输出作为唯一变更说明证据；不得因浏览器缓存缺失跳过页面验证。
- Evidence: `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`、`docs/powershell-preflight-lessons.md`。

### Worktree 门禁

- Trigger: 临时发布 worktree 创建、构建隔离、清理。
- Preflight check: 短路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\m|b|f`；检出冻结提交；删除前确认运行控制台不再引用待删路径。
- Blocker: worktree dirty、提交与冻结基线不一致、路径不在标准边界、未确认改动或未合回提交、运行配置仍指向待删除 worktree。
- Verification: 记录 worktree list、HEAD、status、构建目录、清理结果。
- Forbidden action: 不得复用旧 worktree；不得删除其他任务 worktree；不得对未解析变量路径递归删除。
- Evidence: `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是。本任务不修改业务行为，按发布门禁执行；发现构建/发布契约缺失时 fail fast 并记录。
- 是否存在临时补丁或绕过：否。

## Current Status

completed - 仅测试服发布完成；测试服真实运行态、运行控制台版本号和变更说明验证通过；本任务临时 release worktree 已删除，本地运行控制台已恢复主工作区稳定路径，任务临时证据已按 closeout 规则清理。

## Final Release Evidence

- Release tag: `release-20260712-intmain-test-r260712p-r3`。
- Release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p\m|b|f`。
- Frozen HEAD: maintenance=`481d03c1940f233ba12576801286ff2617e3a441`，backend=`c7753b28997dbd8d8b3581250961646f00b14ccb`，frontend=`2d10335f75a72f934aac52839fdb78a696036304`。
- Build release operation: `op-2026-07-12T031646245278700Z-f1006e17-c7b6-445b-9eaa-5d67e4b66ed1`，status=`SUCCESS`。
- Publish test operation: `op-2026-07-12T043308044248700Z-d8e299c3-a64e-43cc-bd5a-949db86dc67f`，environment=`test`，status=`SUCCESS`。
- Package root: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260712-intmain-test-r260712p-r3`。
- Manifest: sourceRepos backend/frontend 均等于冻结 HEAD 且 dirty=false；publishScope=`code-only`；changeSet.summary=`Release package release-20260712-intmain-test-r260712p-r3`。
- Test runtime: `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health、frontend HTTP、frontend `/release-info.json` 全部通过，见 `evidence/test-server-runtime-verification-r3.json`。
- Forbidden actions: 未执行 `mark-tested`、`promote-prod`、`promote-backup`，未发布正式服或备份服。

## Cleanup Keep

- doc/tasks/20260712-current-head-test-only-release/issues.md

## Closeout Evidence

- Runtime-control restore: 本地 `http://127.0.0.1:48181/actuator/health` 返回 `UP`，运行路径已恢复到 `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`。
- Release worktree cleanup: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p` 已从 Git worktree 注册和物理目录中移除；当前维护仓 `git worktree list --porcelain` 仅保留 `D:\ProjectPackage\Int\IntRuoyiMaintance`。
- Task cleanup: task-closeout apply 已执行，保留 `task.md`、`execution-log.md`、`verification-report.md`、`issues.md`，删除本任务一次性 evidence/helper 文件，避免提交包含明文敏感输出的原始日志。
