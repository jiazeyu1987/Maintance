# Test Plan：测试服 DCC 内容级 Codex 识别跑通

## BDD Scenarios

- `BDD: 维护仓发布链路必须携带 DCC Codex 运行时合同 -> Given 维护仓生成测试服 backend 运行时 / When 输出 .env 和 docker-compose.yml / Then 必须包含 DCC Codex 命令、CODEX_HOME 和挂载。`
- `BDD: backend 容器里缺少 Codex 运行时时不得误判成功 -> Given 容器中没有可执行 codex 或认证目录 / When 触发内容级识别 / Then 后端必须返回明确失败。`
- `BDD: 文件名不足以判断时能通过内容识别完成回写 -> Given 文件名不含唯一明确项目编码 / When 文控从测试服页面触发识别 / Then 后端读取文件内容并由 Codex 返回有效候选。`

## RED

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q`
  - 预期：当前维护仓合同测试先失败，暴露缺少 DCC Codex 运行时变量和挂载。
- `ssh root@172.30.30.58 "docker exec intruoyi-backend /opt/intruoyi/runtime/tools/codex --version"`
  - 预期：当前测试服 v15 现场失败，证明内容识别运行时尚未真正进容器。

## GREEN

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q`
- `python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\verify_contracts.py`
- `ssh root@172.30.30.58 "docker exec intruoyi-backend /opt/intruoyi/runtime/tools/codex --version"`
- `ssh root@172.30.30.58 "docker exec intruoyi-backend test -f /opt/intruoyi/runtime/backend-codex-home/auth.json"`

## REGRESSION

- 保留并复跑维护仓发布合同测试，防止后续全链路发布再次丢失 DCC Codex 运行时合同。
- 若业务后端共享配置有改动，同时回归 DCC 模块识别单测与 Codex CLI 客户端单测。

## E2E

- 必须使用 Playwright 登录测试服管理前端，租户为“测试租户”，账号为 `aoteman`。
- 路径要求：进入真实 DCC 受控文件详情或受控预览页面，点击“识别基础信息”，不能用 API 直接替代最终验收。
- API 仅用于最终校验返回值和定位失败点。

## Test Data

- 真实样本要求：
  - 文件名不包含唯一明确项目编码
  - 文件内容中存在足够证据让 Codex 命中 `dcc_project_code`
  - 允许在测试租户内做真实回写验证
- 账号与入口：
  - 前端：`http://172.30.30.58:8081/`
  - 后端健康检查：`http://172.30.30.58:48081/actuator/health`

## Failure Paths

- 维护仓 `.env` 未写入 `DCC_PROJECT_CODE_CODEX_CLI_COMMAND` 或 `DCC_PROJECT_CODE_CODEX_HOME`
- compose 未传 `CODEX_HOME` 或未挂载 `tools/codex`、`backend-codex-home`
- 容器内 `codex` 可执行文件不存在、无权限或认证目录缺失
- 真实样本仍走文件名快捷路径，无法证明内容识别链路
- 内容识别返回非 JSON、超时或候选无效，但页面/接口没有清晰暴露错误
