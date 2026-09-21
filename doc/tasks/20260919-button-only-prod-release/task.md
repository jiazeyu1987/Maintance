# 20260919-button-only-prod-release

## Task Goal

通过真实运行控制台页面按钮完成一个新的完整发布链路：构建发布包、部署测试服、标记测试通过、点击“上线已验证发布包”发布到正式服。所有写入型发布动作必须由页面按钮触发，不使用接口直调、脚本直调、手工修改远端 `.env`、容器、数据库、迁移台账或发布包。

## Current Status

in_progress — 本地静态/隔离整改完成，待独立复检和真实按钮验收。用户新增强制门禁：整改完成后必须通知用户安排审阅任务 `codex://threads/01a0bd1f-ea37-7112-bdc5-4673055ff2c0` 复检；只有该任务明确给出“同意发布”结论，才能执行测试服部署、mark-tested 或正式服晋级。r105 构建 operation `op-2026-09-21T044719435296100Z-00dbe90b-dc79-46ba-b36f-488d3ebd32e2` 已 FAILED 于本机结构演练，未见本轮部署写入，r105 判废。主程序专用 workflow/API/UI、维护发布器指纹与同包摘要校验、UNKNOWN/备份类型保护及权限迁移 ID 冲突修复已提交并融合本地应用 `int_main=f797a49fa`、维护 `int_main=1ce47ef`；定向/扩大回归、维护 124 项发布套件、权限迁移隔离 MySQL、前端类型及 634 个迁移策略通过。实际控制台尚未加载新提交，配置批准提交/指纹及权限角色授权尚未完成，真实页面与运行态均无新证据，不能宣称发布成功。r106 从未构建且源码冻结已失效；复检前不启动新的构建或任何部署。

## Milestones

1. 锁定本轮新 releaseTag，并确认页面按钮、权限、目标环境与经验门禁。
2. 通过页面按钮执行“构建发布包”，等待 operation 终态并核对 manifest/包完整性。
3. 通过页面按钮执行“部署发布包到测试服”，验证测试服运行态。
4. 通过页面按钮执行“标记测试通过”，绑定恢复候选与 tested 证据。
5. 通过页面按钮执行“上线已验证发布包”，只读验证正式服 operation、manifest、`.env IMAGE_TAG`、实际镜像、backend health、frontend HTTP。
6. 更新任务记录、Go/No-Go 与请求命令日志；若失败，记录真实阻塞并停止。

## 本轮发布冻结

- releaseTag: `release-20260921-button-prod-r106` 原为待复检候选，但本轮整改改变了冻结源，r106 从未构建且不再作为执行候选；复检放行后另建新 worktree、绑定新提交并使用新 tag。r105 在本地 schema rehearsal 失败并判废。
- 维护 worktree: `D:\IntRuoyiWorktree\r260921-prod-release2\m` @ `e357a531da0f8e5e9fbc9c1bbc824fddd9f365bc`
- 应用/前端 worktree: `D:\IntRuoyiWorktree\r260921-prod-release2\a` @ `f97a25ea6ce28abeceed4a6ce1a3e859adf9c357`
- 发布范围: `app-release`，不复制 MySQL/MinIO 业务数据，只执行版本化 required SQL。
- 执行入口: 主程序运行控制台专用 workflow 页面/API；维护仓发布脚本仅作受控执行器。维护 standalone 通用动作不作为正式晋级验收。
- 本轮整改提交: 应用 `f797a49fa99bc8be12590b2f6d4aa2c4e5d3ff8d`；维护实现 `b55c9d2`、融合主干 `1ce47efe7e3e958524cca529ea22b47b478c0d33`。本轮两处临时 worktree 均已提交，未删除；不可当作下一次发布 worktree 复用。

## 复检放行门禁

- 整改完成后先提供源码提交、调用链/发布器指纹、测试、页面非发布路径证据和未覆盖项，通知用户安排上述审阅任务复检。
- 审阅任务明确给出“同意发布”之前，禁止测试服部署、mark-tested、正式服晋级；不得用 standalone、通用 `/actions`、脚本直调或手工改目标状态绕过。
- 本任务本地 PASS、自动续跑和时间经过均不构成复检放行。

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

- 通知角色正式批准为现有角色 `910218`；query-current 权限不是通知接收人依据，不得推断、补造或扩大到 `910231`。
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
