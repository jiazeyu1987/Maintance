# 维护发布固化智能排产冒烟配置执行日志

- 2026-06-18 任务开始。
- 用户需求：发布现在从 `D:\ProjectPackage\Int\IntRuoyiMaintance` 进行，修改必须落到维护仓发布会实际用到的文件。
- BDD: 维护仓发布使用维护仓模板 -> Given 从 IntRuoyiMaintance 执行 build/deploy release When 发布脚本复制 compose Then 使用 ops/deploy/int-ruoyi-test/docker-compose.yml，而不是依赖后端仓 script/deploy 模板。
- BDD: 发布包携带智能排产冒烟运行态 -> Given build-release 或 deploy-release 包含 backend When 发布脚本生成发布目录 Then 包内 docker-compose.yml、.env、smoke runner 和 npm wrapper 均存在，并且 backend 启动参数包含 smoke frontend-directory/script-name。
- BDD: 缺少 smoke runner 源文件会失败 -> Given 前端仓缺少智能排产 smoke E2E 脚本 When 发布 backend Then 发布脚本 fail fast，不生成伪成功发布包。
- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`docs/agent-memory/project-error-prevention.md`、`ci-cd-environment-delivery` 和 `quality-assurance-test-suite` 契约；本任务只修改维护仓本地发布链路，不执行测试服/备份服/正式服写入。
- RED: `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> FAIL，3 failed；维护发布脚本仍从后端仓 `script\deploy` 取 compose，维护 compose 未暴露智能排产 smoke 配置，发布脚本未打包 smoke runner。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> PASS，3 passed。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> PASS。
- GREEN: `python -X utf8 -m pytest scripts\tests -q` -> PASS，5 passed。
- GREEN: `docker compose --env-file <temp> -f ops\deploy\int-ruoyi-test\docker-compose.yml config --services` -> PASS，输出 `mysql/onlyoffice/redis/backend/website/frontend`。
- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\scripts\validate_cicd_environment.py --evidence doc\tasks\20260618-maintenance-persist-scheduler-smoke-release\ci-cd-evidence.md` -> PASS。
- RED: `python -X utf8 C:\Users\BJB110\.codex\skills\quality-assurance-test-suite\scripts\validate_quality_assurance.py --evidence doc\tasks\20260618-maintenance-persist-scheduler-smoke-release\qa-evidence.md` -> FAIL，缺少裸 `RED:`、`GREEN:`、`Verification`、`Blockers` 标记。
- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\quality-assurance-test-suite\scripts\validate_quality_assurance.py --evidence doc\tasks\20260618-maintenance-persist-scheduler-smoke-release\qa-evidence.md` -> PASS。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 ops/deploy/int-ruoyi-test/docker-compose.yml scripts/tests/test_scheduler_smoke_release_config.py doc/tasks/20260618-maintenance-persist-scheduler-smoke-release docs/request-command-log.md` -> PASS，仅 Git 行尾转换提示。
- GREEN: task-closeout-preview -> PASS，保留 4 个任务证据文件，delete/blocked/warnings 均为 `<none>`。
- GREEN: task-closeout-apply -> PASS，保留 4 个任务证据文件，delete/blocked/warnings/deleted_paths 均为 `<none>`。
