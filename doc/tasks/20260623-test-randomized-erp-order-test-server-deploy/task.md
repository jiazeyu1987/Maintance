# 任务：测试服发布随机 ERP 建单改动

## 任务目标

把 `MES 生产工单测试用随机 ERP 建单` 这次前后端改动，按运行控制台真实页面只发布到测试服，不触发正式服或备份服动作，并确保发布输入只包含这次改动对应的干净 worktree 结果。

## 当前状态

COMPLETED：已通过运行控制台真实页面完成 `build-release -> deploy-test`，测试服已切到 `release-20260623-random-erp-test-v1`。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-followup-work-content-wording\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成，与本次发布无直接冲突。

## 经验门禁

- 已读取：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
- 本任务适用强制门禁：
  - 运行控制台页面真实提交，不用命令行替代发布动作。
  - 发布输入必须来自干净 worktree，不能把主仓其他未提交现场混进候选包。
  - 构建前先核对发布包 manifest、sourceRepos、releaseTag 和目标环境。
  - 只发布测试服，不触发正式服或备份服动作。
  - 任何高风险写动作前必须在执行日志里先写 `GREEN: experience-preflight -> PASS`。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是；通过干净 worktree 重放当前测试改动，保证发布输入可追溯且只包含本次变化。
- `是否存在临时补丁或绕过`：否

## BDD 场景

- `BDD: 只发布本次测试改动到测试服 -> Given 干净 release worktree 已重放本次前后端提交 / When 运行控制台页面执行构建发布包并部署测试服 / Then 测试服只切到包含本次随机 ERP 建单改动的新 releaseTag。`
- `BDD: 发布输入必须与干净 worktree 一致 -> Given 页面预览发布命令 / When 运行控制台生成 build-release 和 deploy-test 命令 / Then 命令必须指向本次干净 worktree，而不是主仓其他未提交现场。`
- `BDD: 测试服验证必须暴露真实运行态 -> Given 测试服部署完成 / When 核对运行态 / Then `.env`、镜像和页面都必须显示新 releaseTag，且后端健康与前端入口可用。`

## 里程碑

1. 建立发布任务文档与执行日志。
2. 准备干净 release worktree，并确认只包含本次改动。`DONE`
3. 通过运行控制台页面构建发布包。`DONE`
4. 通过运行控制台页面部署测试服并只读核验运行态。`DONE`

## 预期验证

- `GREEN: experience-preflight -> PASS`
- 运行控制台页面 `build-release` 生成新候选包并产出 manifest
- 运行控制台页面 `deploy-test` 成功
- 测试服 `IMAGE_TAG`、`docker compose ps`、健康检查和前端页面均切换到新 releaseTag

## 已完成工作

- 已确认测试服当前运行 `IMAGE_TAG=20260623_dcc_content_recognition_gateway_timeout_fix_1`。
- 已从当前测试服发布包 manifest 提取本次最小发布基线：
  - backend commit `23c596d1e2ba97ef06b4854b53e80b0e88ec25ed`
  - frontend commit `4ed836cf016975fa6cca74d99b152b9b5ee3891c`
- 已创建发布专用 clean worktree：
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean`
- 已在两套 worktree 上仅重放本次随机 ERP 建单代码改动，不带任务文档。
- backend release worktree 定向单测已通过；frontend release worktree 静态合同与 `ts:check` 已通过。

## 当前阻塞

- 无。

## 完成结果

- 运行控制台页面 `build-release` 已生成候选包 `release-20260623-random-erp-test-v1`，operation=`op-2026-06-23T072156013940200Z-4e4291e1-3c74-4f26-8cda-8c116760c505`，状态 `SUCCESS`。
- 发布包 manifest 已确认：
  - backend commit `aa13420c67513224bebe114d090f0cfffb8388ab`
  - frontend commit `e301a67af7acca887c60d1625d34b87d17409e9f`
  - `publishScope=code-only`
  - frontend `dirty=true` 仅来自用户明确批准带入的 `pnpm-lock.yaml` 修复。
- 运行控制台页面 `deploy-test` 已把测试服切到新包，operation=`op-2026-06-23T074133159825800Z-f54c26d2-d986-42bb-8c53-485f509c8c06`，状态 `SUCCESS`。
- 测试服只读复核确认：
  - `/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260623-random-erp-test-v1`
  - `docker compose ps` 中 `intruoyi-backend` / `intruoyi-frontend` 镜像都为 `release-20260623-random-erp-test-v1`
  - `http://172.30.30.58:48081/actuator/health` 返回 `{"status":"UP"}`
  - `http://172.30.30.58:8081/` 返回 HTTP `200`

## 最终核验

- 页面 `build-release` -> PASS
- 页面 `deploy-test` -> PASS
- 测试服 `.env` / `docker compose ps` / 健康检查 / 前端入口 -> PASS
