# 任务: 维护发布固化智能排产冒烟配置

## 任务目标

- 将智能排产冒烟运行配置固化到 `D:\ProjectPackage\Int\IntRuoyiMaintance` 的发布链路中。
- 确保后续从维护仓发布到测试服时，发布包会自动携带 smoke compose 配置、`.env` 默认项、smoke runner 和 npm wrapper，不再依赖测试服手工修改。
- 不再把 `D:\ProjectPackage\Int\IntRuoyi` 作为本任务构建发布入口。

## 上一任务检查

- 上一任务：`doc/tasks/20260618-deploy-test-slim-release/`。
- 状态：`completed`。
- 处理：上一任务已完成，本任务可以开始。

## 授权范围

- 用户需求：“现在发布是 `D:\ProjectPackage\Int\IntRuoyiMaintance` 里进行发布，修改的内容要是 `D:\ProjectPackage\Int\IntRuoyiMaintance` 里发布会用到的，不在这个目录下构建发布了”。
- 允许：修改维护仓发布脚本、维护仓 compose 模板、维护仓脚本测试和任务文档。
- 禁止：正式服/备份服操作；测试服部署；把敏感账号密码写入仓库；用手工 SSH 修改替代发布脚本固化。

## 经验门禁

- 来源：`docs/experience-index.md`。
- 命中文档：
  - `docs/release-build-preflight-lessons.md`：维护控制台修改后必须用实际脚本/测试确认发布链路已生效；发布预览不能包含正式服、备份、恢复或回滚动作。
  - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布包成功出口以 manifest、runtime env、镜像和 operation 为准；不得用健康检查或手工修改替代发布结果。
  - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服写入/重启/发布必须有当前任务授权；本任务只改本地维护仓，不执行远端写入。
  - `docs/agent-memory/project-error-prevention.md`：环境发布验证不能只看健康，必须核 operation、manifest、远端 IMAGE_TAG/镜像、迁移状态和真实浏览器入口。
- 适用强制门禁：
  - 本任务不执行远端写入；若后续发布，必须另行记录 `GREEN: experience-preflight -> PASS` 并走运行控制台/发布脚本正式路径。
  - 只固化非敏感默认值；租户账号密码等真实 smoke 参数保留远端 `.env` 已有值，不写入仓库。
  - 维护仓发布脚本必须使用维护仓 compose 模板，避免改到非发布入口。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。缺少 smoke runner 源文件、compose 模板或 npm wrapper 时发布脚本 fail fast。
- `是否从根因和长期维护角度解决`：是。发布源头迁回维护仓的脚本和模板，避免测试服手工改 compose。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 维护仓发布使用维护仓模板 -> Given 从 IntRuoyiMaintance 执行 build/deploy release When 发布脚本复制 compose Then 使用 ops/deploy/int-ruoyi-test/docker-compose.yml，而不是依赖后端仓 script/deploy 模板。`
- `BDD: 发布包携带智能排产冒烟运行态 -> Given build-release 或 deploy-release 包含 backend When 发布脚本生成发布目录 Then 包内 docker-compose.yml、.env、smoke runner 和 npm wrapper 均存在，并且 backend 启动参数包含 smoke frontend-directory/script-name。`
- `BDD: 缺少 smoke runner 源文件会失败 -> Given 前端仓缺少智能排产 smoke E2E 脚本 When 发布 backend Then 发布脚本 fail fast，不生成伪成功发布包。`

## 里程碑

- [x] M1 建立任务文档、读取经验门禁并确认上一任务完成。
- [x] M2 RED：新增维护发布 smoke 固化契约测试并复现失败。
- [x] M3 GREEN：修改维护发布脚本和维护 compose 模板。
- [x] M4 回归验证：脚本测试和 PowerShell 解析通过。
- [x] M5 证据、cleanup 预览和提交。

## 预期验证

- `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q`。
- PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1`。
- `git diff --check` 限定本任务文件通过。

## 当前状态

completed

## 当前验证

- `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> PASS，3 passed。
- PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> PASS。
- `python -X utf8 -m pytest scripts\tests -q` -> PASS，5 passed。
- `docker compose --env-file <temp> -f ops\deploy\int-ruoyi-test\docker-compose.yml config --services` -> PASS，服务为 `mysql/onlyoffice/redis/backend/website/frontend`。
- `validate_cicd_environment.py --evidence doc\tasks\20260618-maintenance-persist-scheduler-smoke-release\ci-cd-evidence.md` -> PASS。
- `validate_quality_assurance.py --evidence doc\tasks\20260618-maintenance-persist-scheduler-smoke-release\qa-evidence.md` -> PASS。
- `git diff --check` 限定本任务文件 -> PASS，仅 Git 行尾转换提示。
- `task-closeout-cleanup --mode preview` -> PASS，无删除项、阻塞项或警告。
- `task-closeout-cleanup --mode apply` -> PASS，无删除项、阻塞项、警告或删除路径。

## Current Status

completed

## Cleanup Keep

- `doc/tasks/20260618-maintenance-persist-scheduler-smoke-release/task.md`
- `doc/tasks/20260618-maintenance-persist-scheduler-smoke-release/execution-log.md`
- `doc/tasks/20260618-maintenance-persist-scheduler-smoke-release/ci-cd-evidence.md`
- `doc/tasks/20260618-maintenance-persist-scheduler-smoke-release/qa-evidence.md`
