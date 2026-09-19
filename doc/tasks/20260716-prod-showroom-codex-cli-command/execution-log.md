# 执行日志：正式服展厅一键翻译 Codex CLI 命令契约修复

## BDD

- BDD: 展厅一键翻译使用发布契约中的 Codex CLI 路径 -> Given 正式服后端容器已挂载 `/opt/intruoyi/runtime/tools/codex` 且 `CODEX_HOME` 已配置, When 管理端触发展厅产品一键翻译, Then 后端应执行 `/opt/intruoyi/runtime/tools/codex` 而不是依赖 PATH 中的裸 `codex` 命令。

## TDD / Verification Evidence

- RED: production-runtime-probe -> FAIL, 正式服后端容器内 `PATH=/opt/java/openjdk/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`，`command -v codex` 为空，但 `/opt/intruoyi/runtime/tools/codex` 存在且可执行；当前 Java 启动参数未包含 `--yudao.ai.codex-cli.command`。
- GREEN: experience-preflight -> PASS, 已读取服务器访问、登录、发布备份恢复、维护仓 AGENTS、维护仓经验索引、PowerShell 门禁、bug 回归修复技能与 CI/CD 技能；用户已授权正式服故障处理。后续正式服写入/重启仅限后端展厅 Codex CLI 配置修复与健康验证。
- RED: contract-test-before-fix -> FAIL, `test_publish_runtime_preserves_showroom_codex_linux_contract` 缺少 `ShowroomCodexCliCommand` 发布契约。
- GREEN: contract-test-after-fix -> PASS, `python -X utf8 -m pytest D:/ProjectPackage/Int/IntRuoyiMaintance/scripts/tests/test_publish_dcc_codex_runtime_contract.py -q`，6 tests passed。
- GREEN: prod-runtime-command-path -> PASS, 正式服后端启动参数已包含 `--yudao.ai.codex-cli.command=/opt/intruoyi/runtime/tools/codex`，健康检查 `UP`，容器内 Codex CLI 版本可读取。
- BLOCKER: codex-proxy-connectivity -> 正式服宿主机和后端容器访问 `http://39.106.23.28:8080` 均超时；`codex exec` 超过 180 秒并停在 reconnect，完整翻译输出验证阻塞。

## Command Intent Log

- 2026-07-16：只读 SSH 检查正式服 `/opt/intruoyi/runtime`、`IMAGE_TAG`、`docker compose ps`、后端容器 PATH、`/opt/intruoyi/runtime/tools/codex` 可执行性和 Java 启动参数；原始包含密钥的命令行输出不写入仓库。
- 2026-07-16：读取维护仓 `ops/deploy/int-ruoyi-test/docker-compose.yml`、`ops/deploy/publish-int-ruoyi.ps1`、`scripts/tests/test_publish_dcc_codex_runtime_contract.py`，确认现有发布契约只覆盖 DCC Codex CLI，不覆盖展厅翻译 `yudao.ai.codex-cli.command`。
- 2026-07-16：更新维护仓发布契约后运行目标 pytest；随后在正式服备份 `.env` 与 `docker-compose.yml`，写入 `SHOWROOM_CODEX_CLI_COMMAND`，仅重建 `intruoyi-backend` 并验证健康。

## Blockers

- 正式服到 Codex 代理 `http://39.106.23.28:8080` 当前连接超时；需要恢复代理或提供新的可达 Codex endpoint/key 后，才能继续真实一键翻译内容验证。
