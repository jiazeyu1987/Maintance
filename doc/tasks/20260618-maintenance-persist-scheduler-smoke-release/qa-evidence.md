# 维护发布固化智能排产冒烟配置 QA 证据

## Scope

- 范围：维护仓发布脚本和 compose 模板中的智能排产冒烟配置固化。

## Requirement To Test Matrix

| Requirement | Test |
| --- | --- |
| 维护仓发布使用维护仓模板 | 静态契约测试检查 `$composeTemplate` 指向 `ops/deploy/int-ruoyi-test/docker-compose.yml` |
| 发布包携带 smoke 运行态 | 静态契约测试检查 compose、`.env`、runner package 和 npm wrapper |
| 缺少 runner 源文件 fail fast | 静态契约测试检查发布脚本存在源文件校验和 Fail 文案 |

## Test Types

- Static release contract validation。
- PowerShell parser validation。

## Test Data And Fixtures

- 不新增 mock 数据。

## RED

- RED: `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> FAIL，3 failed。
- RED: 失败覆盖维护 compose 模板来源、compose smoke 环境/启动参数、发布脚本 smoke runner 打包与 `.env` 输出。

## GREEN

- GREEN: `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> PASS，3 passed。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> PASS。
- GREEN: `python -X utf8 -m pytest scripts\tests -q` -> PASS，5 passed。
- GREEN: `docker compose --env-file <temp> -f ops\deploy\int-ruoyi-test\docker-compose.yml config --services` -> PASS。
- GREEN: `validate_quality_assurance.py --evidence doc\tasks\20260618-maintenance-persist-scheduler-smoke-release\qa-evidence.md` -> PASS。
- GREEN: `task-closeout-cleanup --mode apply` -> PASS，无删除项、阻塞项、警告或删除路径。

## Verification

- Verification: 静态契约、脚本解析、全量脚本测试和 compose 模板解析均通过。

## Failed Skipped Flaky Blocked

- 本任务未部署测试服；发布后远端 `.env`/容器环境复验需在后续发布任务中执行。

## Blockers

- Blockers: 当前无本地验证阻塞；远端发布复验不在本任务范围。

## CI Impact And Release Recommendation

- 可进入后续维护仓真实构建/测试服发布流程；发布后必须复查测试服 `.env` smoke 键、backend 容器环境、smoke runner 目录和 npm wrapper。
