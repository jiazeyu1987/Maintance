# 20260702 DCC 识别版本配置修复

## 任务目标

- 修复测试服 DCC 产品名称/编码识别配置中 `DCC_PROJECT_CODE_RECOGNITION_VERSION` 未传入的问题。
- 发布脚本生成 `.env` 时必须写入识别版本，docker compose 必须传入 `--yudao.dcc.project-code-recognition.version`。
- 测试服运行态补齐该配置，避免任务快照继续落入字面量 `${DCC_PROJECT_CODE_RECOGNITION_VERSION}`。

## 里程碑

- [x] RED：补充发布契约测试，先证明当前配置缺失会失败。
- [x] GREEN：修复发布脚本、测试服 compose 模板和契约测试。
- [x] 运行态：在测试服务器补齐 `.env` 与 compose 参数并重启后端。
- [x] 验证：确认后端启动参数包含 `version=v1`，服务健康。

## 预期验证

- `python -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py -q`
- 测试服 `/opt/intruoyi/runtime/.env` 包含 `DCC_PROJECT_CODE_RECOGNITION_VERSION=v1`。
- 测试服后端进程包含 `--yudao.dcc.project-code-recognition.version=v1`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，发布脚本、compose 模板和运行态配置同步修复。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- PowerShell 门禁：已按 `docs/powershell-memory.md` 使用显式 UTF-8 输出和避免 `&&`。
- 服务器门禁：仅操作用户授权的测试服务器配置，不触碰正式服/备份服。
- 发布链路门禁：本次涉及 compose 和发布脚本，补充契约测试覆盖新增配置。

## 验证结果

- RED：`python -m pytest scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` 先失败，原因是发布脚本和 compose 模板缺少识别版本配置。
- GREEN：`python -m pytest scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` 通过，4 passed。
- 测试服运行态：`/opt/intruoyi/runtime/.env` 已包含 `DCC_PROJECT_CODE_RECOGNITION_VERSION=v1`。
- 测试服后端启动参数：已确认包含 `--yudao.dcc.project-code-recognition.version=v1`。
- 测试服健康检查：`http://127.0.0.1:48081/actuator/health` 返回 `{"status":"UP"}`。

## 当前状态

- 已完成。
