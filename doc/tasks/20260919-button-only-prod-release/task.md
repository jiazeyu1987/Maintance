# 20260919-button-only-prod-release

## Task Goal

通过真实运行控制台页面按钮完成一个新的完整发布链路：构建发布包、部署测试服、标记测试通过、点击“上线已验证发布包”发布到正式服。所有写入型发布动作必须由页面按钮触发，不使用接口直调、脚本直调、手工修改远端 `.env`、容器、数据库、迁移台账或发布包。

## Current Status

blocked — 第二轮复审确认当前应用提交 `2692fb881` 曾包含未经业务批准的通知角色替代逻辑；已在后续提交 `5486de0d4` 移除该逻辑并修正 detached HEAD 钩子，在维护提交 `7b6b615` 中补齐租约/心跳/原子恢复与真实 MySQL 隔离测试。本轮复审后又补充了正式晋级按钮参数单测、维护仓恢复锁按钮真实调用契约、发布锁 MySQL 所有权行为测试、以及 MySQL 写入路径失败后的完整回滚测试。当前仍有放行阻塞：正式通知角色、租户和公司范围尚无批准来源；`RuntimeControlOriginalParityTest` 仍有 9 个既有 release package fixture/manifest 基线失败；全量数据库重置分支不纳入本次“不带数据的应用晋级”验收主线，需要单独任务处理。未重新构建或部署，禁止继续 publish-test、mark-tested 或 promote-prod。

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

- 是否引入 fallback/降级/吞异常：否；SSH 非零退出码必须失败，不能仅凭成功字符串放行；锁恢复必须同时满足本机执行器终态、远端所有权、租约、心跳和迁移证据。
- 是否从根因和长期维护角度解决：是；发布锁恢复由受控按钮、精确 operation/releaseTag、执行器检查、迁移证据检查和结构化脚本共同约束。
- 是否存在临时补丁或绕过：否。

## 修复门禁

- 通知角色只能来自正式批准的 `infra_job.handler_param.roleIds` 契约；query-current 权限不是通知接收人依据，缺失映射必须 fail-fast。
- `infra_job` 参数与 role-company scope 写入必须由同一显式事务保护，并有真实 MySQL 正常、缺失角色、租户隔离、失败回滚和幂等证据。
- 锁恢复必须绑定 operation、宿主、进程、身份、租约和心跳；恢复更新使用精确所有权条件，旧执行器失去写入资格，SSH 非零结果不得以成功字符串放行。
- 完整定向测试必须 6/6 通过；新增静态测试不能替代真实 SQL/锁行为验证；禁止 `--no-verify`。
- 新发布前必须同步批准提交、确认控制台实际加载提交、确认无并发 RUNNING 构建并使用项目固定 Playwright 版本。

## 经验门禁

- Trigger: `build-release`、`publish-test`、`recover-test-release-lock`、`mark-tested`、`promote-prod`。
  - Preflight check: 发布前必须锁定单一 releaseTag；按钮必须绑定服务端 workflow、manifest/package digest、测试 operation/验收证据与正式目标；高风险动作前记录 `GREEN: experience-preflight -> PASS`。
  - Blocker: 旧 generic 手填 releaseTag/目标环境直接生产动作、缺少 manifest/checksum、tested attestation、恢复候选、正式 dry-run evidence、页面按钮置灰、目标环境锁或运行中 operation 时必须停止。
  - Verification: 每一步记录页面按钮、operation、目标、终态与运行态证据；正式服最终核 operation、manifest、`.env IMAGE_TAG`、实际镜像、health、HTTP。
  - Forbidden action: 禁止 API-only/mock 代替真实按钮路径；禁止修改不可变包、手工改远端 `.env`/容器/DB/lock/tested；禁止拼接不同 releaseTag。
  - Evidence: `docs/release-agent-checklist.md#5.0 “已测试包发布正式服”按钮入口门禁`、`docs/release-build-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`。
