# CI/CD Evidence：正式服展厅一键翻译 Codex CLI 命令契约

## Bug Summary

- 正式服展厅产品一键翻译最近失败项显示 `INT-83: Failed to execute local codex cli command codex`。
- 根因方向：后端容器有可执行工具 `/opt/intruoyi/runtime/tools/codex`，但展厅翻译 `CodexCliChatModel` 默认执行裸命令 `codex`，而后端容器 PATH 不存在该命令。

## Expected Behavior

- 发布脚本生成的运行时配置必须把展厅翻译 Codex CLI 命令显式绑定到 `/opt/intruoyi/runtime/tools/codex`。
- 后续发布或重建容器后，`CodexCliChatModel` 不依赖宿主机或容器 PATH 中的裸 `codex`。

## Environments And Targets

- Production host: `172.30.30.57`
- Runtime dir: `/opt/intruoyi/runtime`
- Backend container: `intruoyi-backend`
- Release tag observed: `release-20260716-intmain-codeonly-three-env-r260716d-r1`

## Pipeline Files Changed

- `ops/deploy/publish-int-ruoyi.ps1`
- `ops/deploy/int-ruoyi-test/docker-compose.yml`
- `scripts/tests/test_publish_dcc_codex_runtime_contract.py`

## RED Evidence

- RED: `python -X utf8 -m pytest D:/ProjectPackage/Int/IntRuoyiMaintance/scripts/tests/test_publish_dcc_codex_runtime_contract.py -q` -> FAIL, `test_publish_runtime_preserves_showroom_codex_linux_contract` 缺少 `ShowroomCodexCliCommand`。

## GREEN Evidence

- GREEN: `python -X utf8 -m pytest D:/ProjectPackage/Int/IntRuoyiMaintance/scripts/tests/test_publish_dcc_codex_runtime_contract.py -q` -> PASS, 6 tests。
- GREEN: 正式服运行时 `.env` 和 compose 后端参数已包含 `SHOWROOM_CODEX_CLI_COMMAND=/opt/intruoyi/runtime/tools/codex` 与 `--yudao.ai.codex-cli.command=${SHOWROOM_CODEX_CLI_COMMAND}`。
- GREEN: 正式服 `intruoyi-backend` 重建后健康检查 `UP`，容器内 `/opt/intruoyi/runtime/tools/codex --version` 返回 `codex-cli 0.128.0`。

## Environment

- Production host: `172.30.30.57`
- Runtime directory: `/opt/intruoyi/runtime`
- Backend container: `intruoyi-backend`
- Codex command: `/opt/intruoyi/runtime/tools/codex`

## Commands

- `python -X utf8 -m pytest D:/ProjectPackage/Int/IntRuoyiMaintance/scripts/tests/test_publish_dcc_codex_runtime_contract.py -q`
- 远端只读/写入命令通过 SSH LF stdin 执行；写入范围限定为 `.env`、`docker-compose.yml` 的展厅 Codex CLI 命令配置和 `backend` 服务重建。

## Secrets

- 未写入、记录或提交明文 key、token、私钥、连接串或 SSH 凭据。
- 运行态日志和任务文档只记录非敏感路径、版本和脱敏结论。

## Pipeline

- 发布脚本现在生成 `SHOWROOM_CODEX_CLI_COMMAND`，默认值为 `/opt/intruoyi/runtime/tools/codex`。
- Docker Compose 后端 `ARGS` 现在透传 `--yudao.ai.codex-cli.command=${SHOWROOM_CODEX_CLI_COMMAND}`。

## Verification

- 契约测试 GREEN。
- 正式服后端健康 GREEN。
- Codex 命令路径 GREEN。
- 完整 Codex 内容生成仍被代理连接超时阻塞。

## Blockers

- 正式服到 `http://39.106.23.28:8080` 连接超时，导致 `codex exec` 进入 reconnect 并超过 180 秒；这不是发布契约测试能修复的配置路径问题。

## Rollback

- 若配置导致后端启动失败，回滚方式为恢复本次修改前的远端 `.env` / compose 后端参数并重新启动后端；代码契约回滚为撤销维护仓发布脚本与 compose 测试改动。
