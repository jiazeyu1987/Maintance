# 执行日志

## BDD

- BDD: DCC 识别版本配置随发布进入测试服 -> Given 发布脚本生成测试服运行配置，When DCC 批量识别任务启动，Then 后端启动参数应包含非空 `yudao.dcc.project-code-recognition.version`，识别任务快照不应保存 `${DCC_PROJECT_CODE_RECOGNITION_VERSION}` 字面量。

## TDD

- RED: `python -m pytest scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` -> FAIL, 发布脚本缺少 `DCC_PROJECT_CODE_RECOGNITION_VERSION` 参数、`.env` 输出和 compose 启动参数。
- GREEN: `python -m pytest scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` -> PASS, 4 passed。

## 运行态验证

- GREEN: test-server-env -> PASS, `/opt/intruoyi/runtime/.env` 已写入 `DCC_PROJECT_CODE_RECOGNITION_VERSION=v1`。
- GREEN: test-server-compose -> PASS, compose 渲染参数包含 `--yudao.dcc.project-code-recognition.version=v1`。
- GREEN: test-server-backend-args -> PASS, 后端进程命令行包含 `--yudao.dcc.project-code-recognition.version=v1`。
- GREEN: test-server-health -> PASS, `/actuator/health` 返回 `{"status":"UP"}`。
