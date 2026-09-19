# 任务：正式服展厅一键翻译 Codex CLI 命令契约修复

## Task Goal

- 修复正式服展厅产品“一键翻译”最近失败项 `INT-83` 报错 `Failed to execute local codex cli command codex`。
- 将展厅翻译使用的 `yudao.ai.codex-cli.command` 纳入维护仓发布契约，指向已部署的 `/opt/intruoyi/runtime/tools/codex`，避免后续发布后再次丢失。

## Milestones

- [ ] M1：建立维护仓任务记录与经验门禁。
- [ ] M2：新增 RED 契约测试，证明发布脚本和 compose 尚未透传展厅 Codex CLI 命令。
- [ ] M3：更新发布脚本、运行时 `.env` 生成和 Docker Compose 后端参数。
- [ ] M4：运行目标测试 GREEN，并在正式服应用最小配置修复与重启验证。
- [ ] M5：记录证据、提交本任务实现变更，并完成收尾。

## Expected Verification

- `scripts/tests/test_publish_dcc_codex_runtime_contract.py` 覆盖并通过展厅翻译 Codex CLI 命令契约。
- 正式服后端容器启动参数包含 `--yudao.ai.codex-cli.command=/opt/intruoyi/runtime/tools/codex`。
- 正式服后端健康检查通过，容器内 `/opt/intruoyi/runtime/tools/codex --version` 可执行。
- 一键翻译失败根因不再是 `Cannot run program "codex"` / `Failed to execute local codex cli command codex`。

## 经验门禁

- PowerShell / SSH：按 `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md` 与维护仓 `docs/powershell-preflight-lessons.md`，复杂远端命令优先用 ASCII stdin 脚本，避免 PowerShell 引号、CRLF 与 `$()` 污染；命令输出含凭据时必须脱敏，不提交原始密钥日志。
- 发布 / 正式服：已读取 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`docs/login-access.md`、`docs/release-backup-restore.md`；正式服操作已有用户当前任务授权，写入/重启前记录目标主机、目录、容器和影响。
- 维护仓发布契约：后端产物或环境变量契约变更时，维护仓脚本与测试必须同步修改；不得只在正式服手工修补。
- CI/CD：按 `ci-cd-environment-delivery` 技能，新增配置检查先 RED，再最小实现 GREEN；不得伪造绿色部署状态或写入密钥。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，修复发布契约中展厅 Codex CLI 命令未透传的根因。
- 是否存在临时补丁或绕过：否。

## Current Status

blocked

## Progress Log

- 2026-07-16：正式服只读核对确认后端容器内存在 `/opt/intruoyi/runtime/tools/codex`，但 Java 展厅翻译默认执行 `codex`，容器 PATH 中无 `codex` 命令；维护仓发布契约尚未透传 `yudao.ai.codex-cli.command`。
- 2026-07-16：已补齐维护仓发布契约并通过测试；正式服后端已应用配置并健康恢复。完整 Codex 内容生成被 `39.106.23.28:8080` 连接超时阻塞，任务暂不能标记完成。
