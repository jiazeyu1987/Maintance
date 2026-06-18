# 维护发布固化智能排产冒烟配置 CI/CD 证据

## Environments And Deployment Targets

- 本地维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`。
- 发布目标源头：`ops/deploy/publish-int-ruoyi.ps1`。
- 测试服目标：本任务不部署；后续发布目标为 `172.30.30.58:/opt/intruoyi/runtime`。

## Build Test Lint Package Deploy Rollback Commands

- RED：`python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> FAIL，3 failed。
- GREEN：`python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> PASS，3 passed。
- GREEN：PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> PASS。
- GREEN：`python -X utf8 -m pytest scripts\tests -q` -> PASS，5 passed。
- GREEN：`docker compose --env-file <temp> -f ops\deploy\int-ruoyi-test\docker-compose.yml config --services` -> PASS。
- GREEN：`validate_cicd_environment.py --evidence doc\tasks\20260618-maintenance-persist-scheduler-smoke-release\ci-cd-evidence.md` -> PASS。
- GREEN：`git diff --check` 限定本任务文件 -> PASS，仅 Git 行尾转换提示。
- GREEN：`task-closeout-cleanup --mode preview` -> PASS，无删除项、阻塞项或警告。
- GREEN：`task-closeout-cleanup --mode apply` -> PASS，无删除项、阻塞项、警告或删除路径。

## Pipeline Files Changed

- `ops/deploy/publish-int-ruoyi.ps1`：发布脚本改为使用维护仓 compose 模板；新增 smoke runner 打包、远端复制、运行态断言和 `.env` smoke 默认项。
- `ops/deploy/int-ruoyi-test/docker-compose.yml`：backend 环境、启动参数和 npm wrapper 挂载新增智能排产 smoke 配置。
- `scripts/tests/test_scheduler_smoke_release_config.py`：新增维护发布 smoke 固化契约测试。

## Required Secrets And Owners

- 本任务不得新增仓库明文密钥。
- smoke 账号密码等真实运行参数必须沿用目标环境 `.env` 已有值或由运维安全注入。

## Artifact And Release Output

- 本任务不生成发布包，不部署测试服。

## RED Evidence

- `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> FAIL，3 failed。
- 缺口：维护发布脚本未使用维护仓 compose 模板，维护 compose 未包含 smoke 运行态，发布脚本未打包 smoke runner。

## GREEN Verification Evidence

- 维护仓发布 smoke 固化契约测试通过。
- 维护发布脚本 PowerShell 解析通过。
- 维护仓全部脚本测试通过。
- 维护 compose 模板可被 Docker Compose 解析。

## Manual Approvals And Blockers

- 用户已明确维护仓才是发布入口。
- 当前无本地验证阻塞；本任务未发布测试服。

## Rollback Procedure And Validation

- 本任务未发布，无服务器回滚。
- 若后续发布失败，按发布包 releaseTag/manifest 和测试服 `.env`/镜像 tag 回滚。
