# 2026-08-11 当前 HEAD 仅测试服发布

## Task Goal

在任务启动时冻结维护仓和 IntRuoyi 主程序仓当前分支最新已提交 HEAD，只使用本轮专用干净临时发布 worktree 中的已提交内容构建维护控制台和测试发布包，仅执行测试服发布，并完成发布包、manifest、版本号、变更说明、真实运行态、运行控制台页面、问题记录和经验沉淀验收。构建开始后不追逐后续提交，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Milestones

- [x] 启动门禁：核对上一同类任务已 completed，读取发布、服务器、worktree、PowerShell、CI/CD 与运行控制台经验文档。
- [x] Git / worktree 门禁：记录当前分支、冻结提交、主工作区状态、构建目录和本轮专用干净 worktree。
- [x] 构建门禁：基于冻结 worktree 构建维护控制台和测试发布包，验证 manifest、版本号、变更说明和构建来源。
- [x] 测试服发布：仅执行同一 releaseTag 的 `publish-test`，不触发正式服、备份服或 `mark-tested`。
- [x] 真实运行态验收：验证 operation、远端 `.env IMAGE_TAG`、实际镜像 tag、容器、健康检查、前端 HTTP/页面和运行控制台版本信息。
- [x] 问题记录与阶段复盘：记录全部异常、重复操作、耗时点、原因、处理、结果及可前置/自动化判断。
- [x] 经验沉淀与收尾：将本轮问题沉淀到既有前置经验文档，执行 closeout 清理并记录最终结果。

## Expected Verification

- 记录维护仓与主程序仓的 `git status --short --branch`、分支名、冻结 HEAD、dirty 状态摘要和状态哈希。
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
- 长操作：publish-test 期间只要 operation 日志和 migration 状态持续推进，不重复提交；如果无 manifest、无版本说明或 releaseTag 漂移，必须 fail fast。
- 收尾：发布验证完成后先置为 `ready_for_closeout`，再运行 task-closeout cleanup；清理 release worktree 前确认无新提交、clean、无进程引用和物理路径残留。

## Release Baseline

- release id：`r260811a`；计划 releaseTag：`release-20260811-intmain-head-test-r260811a-r1`。
- 维护仓：branch=`int_main`，HEAD=`697f81688bf80527e9a3a7e4a680e8656f0e05b0`，last commit=`任务: 完成当前HEAD仅测试服发布`，主工作区 dirty count 初查约 `162`，status SHA256=`d99fbe0c76c5c6550cc00d94112edb39f137026d994954a759d89aeabb17bde7`。
- 主程序仓：Git root=`E:\IntRuoyi`，branch=`int_main`，HEAD=`5699b804576851ea8cdebf36045d381f044fb5e8`，last commit=`docs: complete PQC leader form release flow`，主工作区 dirty 且 ahead origin/int_main 7；初查 status 输出包含 target_corrupt 目录 warning，需在 clean release worktree 中重新确认构建来源。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a\m`，detached HEAD 匹配冻结提交，创建后 clean。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260811a-release-app`，detached HEAD 匹配冻结提交，创建后 clean。
- 运行控制台 state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a-state`，启动前不存在。
- 构建目录：维护控制台在维护 release worktree；IntRuoyi 后端/前端在主程序 release worktree。

## Blockers

- 当前无发布阻塞；测试服发布和运行态验证已通过，任务进入 closeout 清理阶段。

## Release Result

- 最终 releaseTag：`release-20260811-intmain-head-test-r260811a-r2`。
- build-release operation：`op-2026-08-10T180157565021500Z-7a75427f-088a-4ec9-8fb7-74ac81973a84`，状态 `SUCCESS`。
- publish-test operation：`op-2026-08-10T184419479334Z-b3dd4c79-c0f1-4a8c-bc32-5a930700a511`，状态 `SUCCESS`。
- 测试服运行态：`.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP 200、PDF worker 200、release-info、release lock=`APPLIED`、migration counts=`APPLIED 5 / SKIPPED_ALREADY_APPLIED 419` 均匹配最终 releaseTag。
- 运行控制台页面：Playwright 验证本机 `http://127.0.0.1:48182/` 显示测试服版本 `release-20260811-intmain-head-test-r260811a-r2`、软件版本 `2026.06.0`、发布包与组件范围变更说明。
- 禁止动作：未执行 `mark-tested`、`promote-prod`、`promote-backup`。

## Cleanup Candidates

- `output/playwright/20260811-head-test-only-release`

## Final Closeout

- closeout cleanup：`task-closeout-cleanup` preview/apply 均通过；仓库内一次性证据和临时 Playwright 输出已清理，仅保留 `task.md`、`execution-log.md`、`verification-report.md`。
- release worktree 清理：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a\m`、`D:\IntRuoyiWorktree\r260811a-release-app`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a-state` 均不存在；维护仓与主程序仓 worktree 注册均无 `r260811a`。
- 运行控制台清理：本轮隔离端口 `48182` 无监听。
- 清理后测试服复核：`.env IMAGE_TAG=release-20260811-intmain-head-test-r260811a-r2`，backend/frontend 镜像 tag 匹配，容器 running，backend health=`UP`，frontend HTTP 200。
- 最终状态：completed。
