# Development Plan：测试服 DCC 内容级 Codex 识别跑通

## Milestones

### M1. 用维护仓合同测试锁定根因

- 只读对比维护仓与业务后端仓发布链路差异。
- 在维护仓新增或扩展文本合同测试，先复现：
  - 缺少 `DCC_PROJECT_CODE_CODEX_CLI_COMMAND`
  - 缺少 `DCC_PROJECT_CODE_CODEX_HOME`
  - 缺少 `CODEX_HOME`
  - 缺少 `/opt/intruoyi/runtime/tools/codex` 与 `/opt/intruoyi/runtime/backend-codex-home` 挂载

### M2. 修复维护仓发布链路

- 在 `ops/deploy/publish-int-ruoyi.ps1` 中补齐 DCC Codex 参数解析、默认值继承和 `.env` 写入。
- 在 `ops/deploy/int-ruoyi-test/docker-compose.yml` 中补齐 backend 环境变量和挂载。
- 必要时补发布前/发布后 fail-fast 校验，确保“命令存在、认证目录存在、容器内可执行”。

### M3. 重建测试服 backend 运行时

- 使用维护仓正式发布入口重建测试服 backend。
- 记录 `experience-preflight` 后执行测试服 backend 发布。
- 发布后只读检查：
  - 远端 `.env`
  - 远端 `docker-compose.yml`
  - 容器内 `codex --version`
  - `backend-codex-home/config.toml`、`auth.json`

### M4. 真实内容识别验收

- 选定真实样本：文件名不足以唯一识别，但文件内容可判断。
- 用 Playwright 登录测试服并通过真实前端路径触发识别。
- 再用 API 和数据库回读做最终校验，证明走的是内容级识别而不是文件名快捷路径。

## Implementation Steps

1. 在维护仓 `scripts/tests/` 下新增 DCC Codex 发布合同测试，先让当前缺口以 RED 暴露出来。
2. 修改 `ops/deploy/publish-int-ruoyi.ps1`，为 DCC Codex CLI 命令、`CODEX_HOME`、远端运行时目录与 `.env` 输出建立正式合同。
3. 修改 `ops/deploy/int-ruoyi-test/docker-compose.yml`，把 DCC Codex 环境变量和挂载传入 backend 容器。
4. 如有必要，在维护仓新增远端运行时校验命令，确保容器重建前后都能证明资产到位。
5. 通过正式入口发布测试服 backend，随后执行容器内和真实页面验收。

## Files and Modules

- `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\int-ruoyi-test\docker-compose.yml`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_dcc_codex_runtime_contract.py`
- 如确有必要再补：
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-server\src\main\resources\application-dev.yaml`
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-server\src\main\resources\application-local.yaml`

## Verification Gates

- Gate 1：维护仓合同测试先 RED 后 GREEN。
- Gate 2：发布后容器内 `codex --version` 与 `backend-codex-home` 校验通过。
- Gate 3：真实内容识别样本必须通过 Playwright 前端路径成功触发。
- Gate 4：API 与数据库回读必须同时证明项目编码、项目名称和回写字段正确。

## Rollback or Stop Conditions

- 未获得测试服写入/重建授权时，停止在任务包阶段，不进入实现或发布。
- 若最终验证样本仍被文件名快捷路径覆盖，停止验收并先与第一任务对齐短编码/直连规则。
- 若方案要求把认证文件入仓、写进 compose 模板或明文写入任务文档，立即停止。
- 若维护仓合同已修复但业务后端共享配置仍会在 Linux 运行时回落 `cmd.exe /c codex.cmd`，暂停发布，先补共享配置 fail-fast 或平台合同。
