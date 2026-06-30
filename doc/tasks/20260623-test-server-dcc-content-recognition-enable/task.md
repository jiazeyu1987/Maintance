# 任务：测试服 DCC 内容识别运行时合同补齐

## 任务目标

修复维护仓发布链路缺少 DCC Codex 运行时合同的问题，让测试服 backend 发布包能够稳定携带内容级 DCC 识别所需的命令、`CODEX_HOME` 和挂载。

## 当前状态

PARTIALLY_COMPLETED：测试服 backend/frontend 已完成重建，Codex CLI 运行时、认证同步和 `8081` 代理超时都已打通；当前剩余阻塞不再是环境，而是“可访问且可命中的真实样本”尚未找到。现有样本要么对象缺失，要么 backend 返回 `DCC project-code recognition returned no DCC basic-data match`。

## Current Status

PARTIALLY_COMPLETED

## 上一任务检查

- 上一个维护仓相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-test-server-dcc-codex-recognition-audit\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成只读核验并确认测试服内容识别未跑通；本任务先只做本地发布链路合同修复，不直接执行测试服写入。

## 经验门禁

- 已读取：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
- 本任务适用强制门禁：
  - 维护仓发布链路修改必须落在 `D:\ProjectPackage\Int\IntRuoyiMaintance`，不能只在业务源码仓手工补一份。
  - 当前主维护仓工作区存在大量无关脏现场，本任务必须在独立 clean worktree 内完成改动和验证。
  - 在没有 `experience-preflight` 记录前，不执行测试服写入、容器重建或真实联调；本轮仅限本地合同修复。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是
- `是否存在临时补丁或绕过`：否

## BDD 场景

- `BDD: 发布脚本必须写入 DCC Codex 运行时变量 -> Given 维护仓生成测试服 backend 运行时 / When 输出 .env / Then 其中必须包含 DCC 内容识别所需的 Codex 命令和 HOME 变量。`
- `BDD: compose 必须把 DCC Codex 运行时传进 backend 容器 -> Given 维护仓生成测试服 compose / When backend 容器启动 / Then 其中必须包含 `CODEX_HOME`、识别命令参数和对应挂载。`
- `BDD: 本地合同校验失败时不得误判测试服已可用 -> Given 发布链路缺少 DCC Codex 运行时合同 / When 本地合同测试执行 / Then 测试必须直接失败，而不是用健康检查或宿主机现状替代成功。`

## 里程碑

1. 建立 clean maintenance worktree 任务台账并补齐 DCC Codex 运行时 RED 合同测试。`DONE`
2. 修改 publish 脚本和 compose，补齐 DCC Codex 运行时合同。`DONE`
3. 跑通本地合同测试和 CI/CD 证据校验。`DONE`
4. 评估是否已具备进入测试服写入阶段的前置条件。`DONE`
5. 重建测试服并验证内容识别真实链路。`BLOCKED`

## 预期验证

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q`
- `python -X utf8 C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\scripts\validate_cicd_environment.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable\doc\tasks\20260623-test-server-dcc-content-recognition-enable\ci-cd-evidence.md`

## 完成结果

- 本地发布脚本已显式支持 `DCC_PROJECT_CODE_CODEX_CLI_COMMAND` 与 `DCC_PROJECT_CODE_CODEX_HOME`。
- 本地 compose 已显式传入 `CODEX_HOME`、`--yudao.dcc.project-code-recognition.codex-cli-command` 与对应挂载。
- 本地合同测试与 CI/CD 证据校验均已通过。
- 测试服 backend 已升级到 `20260623_dcc_content_recognition_runtime_fix_1`，前后端同步升级到 `20260623_dcc_content_recognition_gateway_timeout_fix_1`。
- 宿主机与 backend 容器内 `codex exec` 最小冒烟均返回 `OK`。
- `8081` 前端网关不再在 60 秒提前返回 `504`，现可等待 backend 真实返回结果。
- 已对 20 条“对象存在、可访问”的测试租户样本执行真实识别采样，结果 `20/20` 返回 `DCC project-code recognition returned no DCC basic-data match`，且数据库回读确认 `dcc_project_code_id` 仍全部为空。
- 剩余阻塞：当前测试服已不存在“运行时未打通”问题，真正阻塞收敛为“现有可访问样本内容不足以命中 DCC 基础数据，或提示词/识别策略对这批样本仍不够强”。
