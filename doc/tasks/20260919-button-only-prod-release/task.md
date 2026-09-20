# 20260919-button-only-prod-release

## Task Goal

通过真实运行控制台页面按钮完成一个新的完整发布链路：构建发布包、部署测试服、标记测试通过、点击“上线已验证发布包”发布到正式服。所有写入型发布动作必须由页面按钮触发，不使用接口直调、脚本直调、手工修改远端 `.env`、容器、数据库、迁移台账或发布包。

## Current Status

in_progress — 当前专用 worktree 为 `D:\IntRuoyiWorktree\r260917-button-publish7\m`。已通过页面按钮新增并执行“恢复测试服发布锁”入口，远端旧 r4 测试锁已从 `RUNNING` 恢复为 `FAILED`，且只读核对旧 r4/r14 迁移证据为 0。恢复操作期间发现 Windows OpenSSH 在远端 SQL 成功后仍可能返回 `close - IO is still pending on closed socket`，已在 worktree 脚本中修复为必须看到 `LOCK_RECOVERED` 且无真实阻塞/SQL/连接错误时才接受该噪音；相关测试 65/65 通过。下一步需提交该修复后使用新的 releaseTag 重新通过页面按钮构建并发布测试服。

## Milestones

1. 锁定本轮新 releaseTag，并确认页面按钮、权限、目标环境与经验门禁。
2. 通过页面按钮执行“构建发布包”，等待 operation 终态并核对 manifest/包完整性。
3. 通过页面按钮执行“部署发布包到测试服”，验证测试服运行态。
4. 通过页面按钮执行“标记测试通过”，绑定恢复候选与 tested 证据。
5. 通过页面按钮执行“上线已验证发布包”，只读验证正式服 operation、manifest、`.env IMAGE_TAG`、实际镜像、backend health、frontend HTTP。
6. 更新任务记录、Go/No-Go 与请求命令日志；若失败，记录真实阻塞并停止。

## Expected Verification

- 所有写入型发布动作均有 Playwright 页面按钮点击证据。
- 同一 releaseTag 完成 `build-release -> publish-test -> mark-tested -> promote-prod`，不拼接旧 tag。
- 正式服成功判定同时满足 operation=SUCCESS、manifest、`.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP=200。
- 任一门禁失败时保持阻塞，不降级、不绕过、不手工补绿。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；Windows OpenSSH socket close 噪音仅在 `LOCK_RECOVERED` 明确出现且无真实错误证据时被归类为已知传输噪音，不会掩盖阻塞、SQL 错误或连接失败。
- 是否从根因和长期维护角度解决：是；发布锁恢复由受控按钮、精确 operation/releaseTag、执行器检查、迁移证据检查和结构化脚本共同约束。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- Trigger: `build-release`、`publish-test`、`recover-test-release-lock`、`mark-tested`、`promote-prod`。
  - Preflight check: 发布前必须锁定单一 releaseTag；按钮必须绑定服务端 workflow、manifest/package digest、测试 operation/验收证据与正式目标；高风险动作前记录 `GREEN: experience-preflight -> PASS`。
  - Blocker: 旧 generic 手填 releaseTag/目标环境直接生产动作、缺少 manifest/checksum、tested attestation、恢复候选、正式 dry-run evidence、页面按钮置灰、目标环境锁或运行中 operation 时必须停止。
  - Verification: 每一步记录页面按钮、operation、目标、终态与运行态证据；正式服最终核 operation、manifest、`.env IMAGE_TAG`、实际镜像、health、HTTP。
  - Forbidden action: 禁止 API-only/mock 代替真实按钮路径；禁止修改不可变包、手工改远端 `.env`/容器/DB/lock/tested；禁止拼接不同 releaseTag。
  - Evidence: `docs/release-agent-checklist.md#5.0 “已测试包发布正式服”按钮入口门禁`、`docs/release-build-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`。
