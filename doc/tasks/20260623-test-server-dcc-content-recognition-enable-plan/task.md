# 任务：测试服 DCC 内容级 Codex 识别跑通

## Goal

把测试服务器 `172.30.30.58` 上 DCC 文件“读取文件内容后交给 Codex 判断项目编码/项目名称”的完整链路跑通，并证明维护仓发布链路生成的测试服运行时能够稳定携带 DCC Codex CLI 运行环境。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-test-server-dcc-codex-recognition-audit\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已确认当前测试服“文件名唯一编码直连可用，但内容级 Codex 识别未跑通”；本任务在此基础上把运行时、发布链路和真实验证补齐。

## Scope

- 维护仓发布链路：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\int-ruoyi-test\docker-compose.yml`
- 维护仓发布回归测试：
  - 新增或扩展 `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\*.py`
- 测试服运行时资产：
  - `/opt/intruoyi/runtime/tools/codex`
  - `/opt/intruoyi/runtime/backend-codex-home`
  - 测试服后端容器 `intruoyi-backend`
- 真实验证路径：
  - 后端容器可执行 Codex CLI
  - 真实样本走“文件名不足以判断 -> 读取文件内容 -> Codex 返回候选 -> 回写成功”

## Non-Scope

- 正式服、备份服部署
- `dcc_project_code` 基础数据人工修正
- 短编码直连规则硬化（由 `20260623-dcc-short-code-recognition-hardening-plan` 独立处理）
- 任何把密钥或认证文件写入仓库的做法

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
- 强制门禁摘录：
  - 测试服写入、容器重建、发布和真实联调前，必须记录 `GREEN: experience-preflight -> PASS`。
  - 发布链路修复必须改维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance`，不能只在业务源码仓手工补一份。
  - 真实 E2E 必须走 Playwright 和真实测试租户，不允许接口绕过前端流程替代最终验收。
  - 远端 `auth.json`、`config.toml` 与任何密钥内容不得入仓，只能以运行时受控方式落地。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。内容识别运行时缺失时必须 fail fast，不允许继续回退成“看起来成功”。
- `是否从根因和长期维护角度解决`：是。优先修复维护仓发布链路缺少 DCC Codex 运行时合同的问题，而不是在测试服容器里手工补一次文件。
- `是否存在临时补丁或绕过`：否。最终方案必须能通过正式发布入口稳定重建测试服运行时。

## BDD 场景

- `BDD: 维护仓发布链路必须携带 DCC Codex 运行时合同 -> Given 维护仓构建测试服 backend 运行时 / When 生成 .env 与 docker-compose.yml / Then 其中必须包含 DCC Codex CLI 命令、CODEX_HOME 和对应挂载路径。`
- `BDD: 测试服后端容器可执行内容识别所需 Codex CLI -> Given 测试服已按修复后的发布链路重建 backend / When 在容器内执行配置的 Codex 命令 / Then 必须返回可执行版本且可读取 backend-codex-home 中的认证配置。`
- `BDD: 文件名不足时必须通过内容识别完成回写 -> Given 真实受控文件文件名不包含唯一明确项目编码 / When 文控在测试服执行基础信息识别 / Then 后端必须读取文件内容、调用 Codex 并回写命中的项目编码与项目名称。`

## Milestones

1. 用维护仓合同测试复现“发布链路未携带 DCC Codex 运行时”的缺口。`COMPLETED`
2. 在维护仓补齐 `.env`、compose、挂载和发布参数的 DCC Codex 运行时合同。`COMPLETED`
3. 重建测试服 backend 运行时，并验证容器内 `codex` 与 `CODEX_HOME` 可用。`COMPLETED`
4. 用真实样本走通内容级 Codex 识别，并完成前端/接口/数据库三点校验。`IN_PROGRESS`

## Expected Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q`
- `python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\verify_contracts.py`
- 只读或发布后验证：
  - `ssh root@172.30.30.58 "docker exec intruoyi-backend /opt/intruoyi/runtime/tools/codex --version"`
  - `ssh root@172.30.30.58 "docker exec intruoyi-backend test -f /opt/intruoyi/runtime/backend-codex-home/auth.json"`
- 最终真实验证：
  - Playwright 打开测试服 DCC 页面并触发“识别基础信息”
  - API 最终校验 `POST /admin-api/dcc/controlled-files/{id}/recognize-project-code`
  - 数据库回读 `dcc_controlled_file` / `dcc_controlled_file_master`

## Blockers

- 用户已授权测试服写入、容器重建和真实联调，原始授权阻塞已解除。
- 当前测试租户可见的中等规模目录样本已能跑完 Linux Codex 内容识别链路，但最新 `12` 条目录样本最终全部返回 `DCC project-code recognition returned no DCC basic-data match`；因此还缺一个“测试租户可见、文件名不足、但文件内容应能稳定命中”的真实样本，才能宣告测试服内容识别结果放行。
- 按用户最新要求切到测试服 `芋道源码` 租户采样后，已通过系统现有角色更新接口把 `tenant_id=1` 的 `wenkong` 角色码改为 `doc_control`，`wangsiyu` 现可真实看到批量识别按钮并发起任务；但最新约 `20` 条样本目录仍然只有部分命中，尚未达到“全部跑通”。
- 截至 2026-06-24 晚间，测试服 `芋道源码/wangsiyu` 已完成 4 轮中等规模目录真实批量识别，其中最佳样本为 `质量管理/3.DMR/10.产品技术要求`（`24` 条），结果 `success=7 / failed=17`；说明这条租户和运行时链路下确实存在可持续扩大的正向命中样本。
- 测试服 `芋道源码/wangsiyu` 对 `质量管理/2.DHF`（`directoryId=911730`，递归 `15644` 条）的首轮长跑 `taskId=10` 与二轮 `taskId=11` 都因修复发布带来的 backend 重启被自动收口为 `FAILED`，但这两轮已帮助定位出“精确重复候选未折叠”“Codex 提示词缺目录路径上下文”“目录路径唯一长编码未参与高置信直连”三处根因。
- 截至 `2026-06-24 23:49:35 +08:00`，修复后重新发起的 `taskId=12` 已在测试服 `2.DHF` 长跑样本上跑出 `processed=323 / success=64 / failed=259 / remaining=15321`，证明本轮修复已经显著扩大了真实正向命中样本；但当前长跑已经进入慢速尾段，最近 `4` 次 `95s` 轮询仅新增 `3` 条处理。
- 截至 `2026-06-24 23:54:10 +08:00`，`taskId=12` 已推进到 `processed=326 / success=64 / failed=262 / remaining=15318`；连续两段轮询都未再增长 `successCount`，说明这轮大样本已经进入更慢的尾段。
- 截至 `2026-06-25 00:03:40 +08:00`，`taskId=12` 已推进到 `processed=332 / success=64 / failed=268 / remaining=15312`；凌晨这段轮询确认它没有卡死，但当前新增处理条目仍全部是失败样本，成功数继续停留在 `64`。
- 为了持续跟踪到任务真正结束，当前已在 `artifacts/task-12-monitor/` 下挂起 Python 后台监控器；最新自动快照时间为 `2026-06-25 00:14:05 +0800`，刻度为 `processed=339 / success=64 / failed=275 / remaining=15305 / status=RUNNING`。
- 旧 PowerShell 监控残留已停止，当前只保留 Python 监控器；最新自动快照时间为 `2026-06-25 00:17:45 +0800`，刻度为 `processed=342 / success=64 / failed=278 / remaining=15302 / status=RUNNING`。
- 当前后台监控器已重启为正式 `120s` 轮询节奏（PID `14036`）；最新自动快照时间为 `2026-06-25 00:21:35 +0800`，刻度为 `processed=344 / success=64 / failed=280 / remaining=15300 / status=RUNNING`。
- 后台 Python 监控器下一档自动快照已推进到 `2026-06-25 00:25:36 +0800`，刻度为 `processed=346 / success=64 / failed=282 / remaining=15298 / status=RUNNING`。
- 后台 Python 监控器继续自动推进到 `2026-06-25 00:31:38 +0800`，刻度为 `processed=350 / success=64 / failed=286 / remaining=15294 / status=RUNNING`。
- 后台 Python 监控器继续自动推进到 `2026-06-25 00:37:40 +0800`，刻度为 `processed=354 / success=64 / failed=290 / remaining=15290 / status=RUNNING`。
- 后台 Python 监控器继续自动推进到 `2026-06-25 00:41:41 +0800`，刻度为 `processed=356 / success=64 / failed=292 / remaining=15288 / status=RUNNING`。
- 后台 Python 监控器继续自动推进到 `2026-06-25 00:47:43 +0800`，刻度为 `processed=359 / success=64 / failed=295 / remaining=15285 / status=RUNNING`。
- 远端运行时认证文件来源仍只能复用既有受控配置，不允许把密钥改为仓库静态文件。

## Current Status

IN_PROGRESS：测试服发布链路、Linux Codex 运行时、`300s` 超时合同和批量任务失败消息截断均已修复并完成真实验证；针对 `2.DHF` 长跑样本又追加修复了“精确重复候选折叠”“Codex 目录上下文提示”“目录路径唯一长编码直连”三处识别根因。最新长跑 `taskId=12` 已在 `15644` 条样本上跑出 `64` 条真实成功命中，目前自动监控刻度推进到 `339` 条且仍在 RUNNING，剩余工作仍是持续监控到全部分析完成，并汇总最终命中/失败分布。
