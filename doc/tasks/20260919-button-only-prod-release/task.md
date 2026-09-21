# 20260919-button-only-prod-release

## Task Goal

通过真实运行控制台页面按钮完成一个新的完整发布链路：构建发布包、部署测试服、标记测试通过、点击“上线已验证发布包”发布到正式服。所有写入型发布动作必须由页面按钮触发，不使用接口直调、脚本直调、手工修改远端 `.env`、容器、数据库、迁移台账或发布包。

## Current Status

blocked — 第十轮 R10-1 源码与隔离验证通过，R10-2 本地页面准备部分通过、当前受阻。应用工作树新提交 `c8edc935c` 的 JAR 与独立 48086/8086 页面已核：主程序专用工作流 GET=200，登录后从真实菜单可达，未发现合格 TESTED 包，未执行发布。测试租户登录凭据没有安全来源；既有总览会自动只读探测远端且本机脚本报错，未取得本轮继续远端检查的明确边界前不再触发。任务运行实例现已退出，原 8081/48081/48082 未触碰。审阅任务 `codex://threads/01a0bd1f-ea37-7112-bdc5-4673055ff2c0` 仍为 BLOCKED；r105 判废、r106 未构建且不可复用，未获“同意发布”前不得构建、部署、mark-tested 或晋级。

## Milestones

### 第十轮复检整改（当前）

1. M10-1：本地代码/组件验证 PASS，待运行态复检。预览现重读 NAS manifest/tested、原始和标准测试 operation 文件、维护发布器字节 SHA；RED/GREEN 覆盖漂移、缺失/失效、无授权/无生产 operation/零远端写入，扩大运行控制回归与真实本机 PowerShell 验证 PASS。尚无实际 NAS/服务器成功包验收。
2. M10-2：部分通过/阻塞。隔离 JAR/前端运行身份、8086 主程序真实 admin 登录/菜单入口、新工作流 GET 与按钮原因禁用已验证；测试租户凭据缺失，正式 permission 菜单尚未在本机真实库执行，且总览自动远端只读探测失败。未能通过真实 TESTED 页面发起 production preview，不能伪造包；需要明确安全凭据与远端只读边界后继续。
3. M10-3：静态/隔离验证、两仓提交和本地主干融合后更新任务记录；通知用户安排指定独立审阅任务复检。取得“同意发布”前保留暂停发布。

本轮应用整改工作树沿用同一任务的 `D:\IntRuoyiWorktree\r260921-prod-release2\a`，基提交 `f797a49fa`，只作代码/本地检查，不作为下一次发布 worktree；维护 `m` 仅供只读核对。运行态使用任务独立端口及状态目录，不能占用/停止现有 8081、48081 或其它任务进程。

设计约束检查：不引入 fallback/降级/吞异常；从真实证明合同与源头修正格式和预览核验，长期维护由一个可复用只读检查器负责；不做临时补丁、伪造 TESTED、后台手写成功状态或任何目标服务器写入。

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
- 应用 `origin/int_main` 已推送到 `f797a49fa`；维护仓无 remote，主干仅本地提交。共享请求日志包含并行任务改动，未作为本任务提交暂存。

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
