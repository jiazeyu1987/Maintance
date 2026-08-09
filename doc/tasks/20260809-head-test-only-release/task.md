# 2026-08-09 当前 HEAD 仅测试服发布

## Task Goal

在任务启动时冻结维护仓和 IntRuoyi 主程序仓当前分支最新已提交 HEAD，只用干净临时发布 worktree 中的已提交内容构建维护控制台与测试发布包，仅执行测试服发布，并完成真实运行态、版本号、变更说明、问题记录和经验沉淀验收。构建开始后不追逐后续提交，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Milestones

- [x] 启动门禁：核对上一任务状态，读取命中的发布、服务器、worktree、PowerShell 与运行控制台经验文档。
- [x] Git / worktree 门禁：记录当前分支、冻结提交、主工作区状态、构建目录和本轮专用干净 worktree。
- [x] 构建门禁：基于冻结 worktree 构建维护控制台和测试发布包，验证 manifest、版本号、变更说明和构建来源。
- [x] 测试服发布：仅执行同一 releaseTag 的 `publish-test`，不触发正式服、备份服或 `mark-tested`。
- [x] 真实运行态验收：验证 operation、远端 `.env IMAGE_TAG`、实际镜像 tag、容器、健康检查、前端 HTTP/页面和运行控制台版本信息。
- [x] 问题记录与阶段复盘：记录全部异常、重复操作、耗时点、原因、处理、结果及可前置/自动化判断。
- [x] 经验沉淀与收尾：前置经验已更新；任务控制台、worktree/state 与一次性证据已清理，最终远端复核通过。

## Expected Verification

- 记录维护仓与主程序仓的 `git status --short --branch`、分支名和冻结 HEAD。
- 本轮专用临时发布 worktree 均指向冻结 HEAD，构建前后 Git 状态干净；未提交改动不进入构建产物。
- 发布包根 `manifest.json` 的 releaseTag、component、publishScope、sourceRepos commit/dirty、artifact SHA256、版本号和变更说明均与冻结提交一致。
- 同一 releaseTag 的 `build-release` 与 `publish-test` operation 均为 `SUCCESS`，且未执行禁止动作。
- 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health=UP、frontend HTTP 200、前端页面、release-info、release lock/migration 与运行控制台版本变更说明全部通过。
- `execution-log.md` 完整记录 BDD、经验预检、命令证据、问题清单、阶段复盘和最终结论。

## Current Status

completed

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。任何构建来源、manifest、版本、变更说明、发布 operation 或运行态关键证据无法确认时立即失败并记录。
- 是否从根因和长期维护角度解决：是。发布问题先冻结证据并定位 manifest、migration、脚本契约或环境根因，不以重复发布或跳过验证掩盖。
- 是否存在临时补丁或绕过：否。未获得用户明确批准时不采用临时脚本、mock、默认成功或降级验收。

## 经验门禁

- 冻结来源：发布开始后只认本任务记录的维护仓与主程序仓 HEAD；主工作区脏时必须使用本轮专用 clean worktree，后续提交不纳入本轮。
- 单一链路：仅允许同一 releaseTag 的 `build-release -> publish-test`；禁止 `mark-tested`、`promote-prod`、`promote-backup` 和正式服/备份服写操作。
- Manifest：发布前必须验证发布包根 `manifest.json` 的 sourceRepos commit 与冻结 HEAD 一致、dirty=false、artifact 校验全通过，并确认版本号和变更说明。
- 运行态：operation=SUCCESS 之后仍需验证 `.env IMAGE_TAG`、实际镜像 tag、容器、health、HTTP、页面、release-info、release lock/migration 和运行控制台。
- 高风险动作：服务器写入、发布、真实页面验收、worktree 清理前必须先在 `execution-log.md` 写入 `GREEN: experience-preflight -> PASS`；缺失即阻塞。
- 编码与凭据：PowerShell/SSH 使用明确 UTF-8 和结构化证据；配置与日志不得记录密码、token、私钥或连接凭据。

## Release Baseline

- 维护仓：branch=`int_main`，HEAD=`1978562394fbc722f8b534988ddf1e3f0e4f8846`，主工作区 dirty count=`164`，status SHA256=`5b7666ec61de601aff2ff326015eabddc184f372b8108a2cf8d1596261652ec7`。
- 主程序仓：Git root=`E:\IntRuoyi`，branch=`int_main`，HEAD=`199836c5fc105033898c2df59fb8ca22ac005625`，主工作区 dirty count=`897`，status SHA256=`9d96b2fe48924ae434523b83948289357711d2d14f2a9d6da5d8ea80ca597fd2`。
- release id：`r260809a`；计划 releaseTag=`release-20260809-intmain-head-test-r260809a-r1`。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260809a\m`，detached HEAD 匹配冻结提交且 clean。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260809a-release-app`，detached HEAD 匹配冻结提交且 clean。
- 运行控制台 state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260809a-state`，任务期间隔离使用，closeout 已删除。
- 构建目录：维护控制台在维护 release worktree；IntRuoyi 后端/前端在主程序 release worktree。

## Blockers

- 当前无发布阻塞；主工作区极脏已由专用 clean worktree 方案隔离。

## Release Result

- 维护控制台构建：`scripts/build.ps1` PASS；Maven tests=`26 passed`；JAR SHA256=`054c79ff442ccad4b5fbfd8f55958131b5b7ebdbbf0650098511bf52065ebfd3`。
- `build-release`：operation=`op-2026-08-09T154417143232100Z-1cbd9f9c-35e8-4b3f-9cda-1646af3f808f`，status=`SUCCESS`。
- 发布包：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260809-intmain-head-test-r260809a-r1`；manifest artifact count=`467`，missing=`0`，hash mismatch=`0`；后端/前端 source commit 均为冻结主程序 HEAD，dirty=false；release-info 版本和变更说明一致。
- `publish-test`：operation=`op-2026-08-09T155709667969700Z-6d3f54cc-4892-4b0e-8c49-624bacd79bfe`，status=`SUCCESS`；未执行 `mark-tested`、`promote-prod`、`promote-backup`，未写正式服或备份服。
- 测试服：`.env IMAGE_TAG`、backend/frontend 实际镜像 tag 均匹配本轮 releaseTag；两容器 running；backend health=`UP`；frontend HTTP=`200`；release lock=`APPLIED`；migration failed/running=`0`。
- Playwright：测试服登录页面与运行控制台均 HTTP 200，无 console error/failed request；运行控制台显示本轮 releaseTag、发布包和组件变更说明。

## Cleanup Candidates

- `output/playwright/r260809a-release/`（task-closeout apply 已删除）。

## Cleanup Keep

- `doc/tasks/20260809-head-test-only-release/task.md`
- `doc/tasks/20260809-head-test-only-release/execution-log.md`
- `doc/tasks/20260809-head-test-only-release/verification-report.md`

## Closeout Result

- `task-closeout-cleanup` preview/apply 均通过，blocked/warnings=`none`；任务目录只保留三份正式记录。
- PID 26248 与 48182 listener 均不存在；维护/app release worktree 与 state dir 的 Git 注册、物理路径和进程引用均不存在。
- 两个 release worktree 未产生新提交，无需合回 `int_main`；其它并发 worktree、进程和主工作区改动未触碰。
- worktree/state 清理后的测试服最终 postcheck 仍 PASS；本任务完成。
