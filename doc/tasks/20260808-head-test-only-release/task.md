# 20260808-head-test-only-release

## Task Goal

基于本次发布开始时当前分支 HEAD 的最新已提交代码构建维护控制台和测试发布包，并仅发布到测试服务器。未提交改动不得进入构建产物，禁止执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Milestones

- [x] M1 发布前 Git / 规则 / 经验门禁确认：记录当前分支、HEAD、脏状态、目标提交、构建目录与临时 worktree 路径。
- [x] M2 创建干净临时发布 worktree：证明构建输入仅来自发布开始记录的 HEAD。
- [x] M3 构建维护控制台和测试发布包：检查发布包、manifest、版本号与变更说明。
- [x] M4 仅测试服发布：按现有发布文档执行 `build-release -> publish-test`，不触碰正式服或备份服。
- [x] M5 测试服真实运行态验收：检查镜像 tag、容器状态、健康检查、前端 HTTP、前端页面、运行控制台版本号和变更说明。
- [x] M6 问题记录与阶段复盘：记录 Git、worktree、构建、manifest、脚本、镜像、容器、健康检查、页面、控制台、文档流程和耗时问题。
- [x] M7 经验沉淀与收尾：长期经验已更新；closeout cleanup、运行控制台会话停止、release worktree/state 清理和最终远端复核均完成。

## Expected Verification

- `git status --short --branch`、`git rev-parse HEAD` 和 worktree HEAD 证明构建基于固定提交。
- 发布包根 `manifest.json`、版本号、变更说明与本次目标提交一致。
- 测试服发布 operation 为成功，远端 `.env IMAGE_TAG`、后端/前端实际镜像 tag、容器状态、后端 health、前端 HTTP 200 均通过。
- 通过真实前端页面验证运行控制台显示当前版本号和变更说明。
- 本次问题均记录到 `execution-log.md`，经验沉淀更新长期经验文档和索引。

## Design Constraints Check

- `是否引入 fallback/降级/吞异常`：否；任何缺少构建来源、manifest、版本号、变更说明或运行态证据的情况必须 fail fast。
- `是否从根因和长期维护角度解决`：是；发布只使用 clean worktree 的固定 HEAD 输入，并将问题沉淀为可执行前置门禁。
- `是否存在临时补丁或绕过`：否；不允许未提交改动进入构建产物，不允许跳过测试服真实运行态验证。

## Experience Gate

- `docs/test-release-preflight.md`：仅允许 `build-release -> publish-test`；必须使用本轮专用 clean release worktree 冻结维护仓和主程序 HEAD；manifest/sourceRepos 必须 dirty=false；publish-test preview 必须结构化证明目标为测试服 `172.30.30.58`；发布后 `.env`、镜像、容器、health、HTTP、release-info、运行控制台版本变更说明必须全部匹配同一 releaseTag。
- `docs/release-build-preflight-lessons.md`：构建后必须校验发布包根 `manifest.json`，而不是只看兼容概要；Manifest v1 与 legacy schema 字段需分流；required SQL / migration policy gate 在 build-release 前 fail fast；主工作区 dirty 时不得直接出包。
- `docs/powershell-preflight-lessons.md` 与 `E:\IntRuoyi\docs\powershell-memory.md`：PowerShell 不使用 `&&`；中文、多行、SSH stdin、JSON 和日志写入必须显式 UTF-8；关键命令单独记录退出码，不得让串联命令最终 0 掩盖中间失败。
- `E:\IntRuoyi\docs\worktree-memory.md`：临时 release worktree 使用短路径，未产生新提交则发布完成后删除；清理前必须确认 worktree clean、无未合并提交、运行控制台不再引用该路径。
- `E:\IntRuoyi\docs\server-access.md` 与 `E:\IntRuoyi\docs\login-access.md`：服务器写入仅限测试服授权范围；页面/E2E 使用真实路径验证，不用接口或旧快照替代页面结论。

## Current Status

completed
