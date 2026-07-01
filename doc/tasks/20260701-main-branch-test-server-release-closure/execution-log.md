# 20260701 基于主分支完成测试服务器真实发布闭环执行日志

BDD: 三仓主分支脏改先提交再发布 -> Given 当前维护仓、后端仓、前端仓主工作区存在脏改 When 用户确认先提交主工作区 Then 必须分别提交三仓当前主分支在途成果，并以新提交版本作为本轮发布输入。

BDD: 主分支真实发布测试服闭环 -> Given 三仓主分支输入已提交且运行控制台可用 When 真实执行 `build-release -> publish-test` Then 测试服 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP 必须全部与同一 `releaseTag` 一致。

BDD: 通用问题前移沉淀为事前经验 -> Given 发布过程中出现可复用的阻塞、根因或排查路径 When 本轮发布闭环完成 Then 必须把通用问题补到事前发布经验，把失败排障保留在任务记录或事后材料。

INFO: task-created -> 已创建 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-main-branch-test-server-release-closure\` 任务台账，用于记录本轮 2026-07-01 主分支测试服真实发布闭环。
GREEN: experience-preflight -> PASS，已读取并命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`。
GREEN: user-approved-main-branch-commit-first -> PASS，用户已明确确认先提交当前三仓主工作区，再基于这些新提交执行本轮测试服真实发布。
INFO: dirty-scope-check -> 2026-07-01 当前三仓主分支 `int_main` 均存在脏改：维护仓为 2026-06-30 主分支发布闭环复盘与经验文档更新；后端仓为 2026-07-01 角色配置包、排产台导入错误细化、SRM 管理员菜单范围治理等源码/SQL/测试及任务台账；前端仓为 `zhaojie` 报工归属权限前端显示修复及对应 E2E/任务台账。当前进入分别核对并提交阶段。
