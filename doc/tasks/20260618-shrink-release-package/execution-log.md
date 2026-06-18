# 执行日志: 缩小 code-only 发布包

- 用户需求：低风险缩小发布包，只保留部署必需内容，去掉 `docker-build-context`，预计从 1,392 MiB 降到约 783 MiB。
- 前置读取：`ci-cd-environment-delivery`、`references/cicd-contract.md`、`docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`docs/agent-memory/project-error-prevention.md`。
- `GREEN: prior-task-status -> PASS，上一个任务 20260618-build-test-backup-release 已 completed。`
- `BDD: 构建发布包清理构建上下文 -> Given build-release 已完成 Docker 镜像打包和 manifest 生成, When 发布包复制到 NAS 前进行最终瘦身, Then 发布目录不包含 docker-build-context，且 manifest、release-manifest、镜像 tar、required-sql、ops-runtime 等部署必需内容仍存在。`
- `BDD: 部署仍可读取发布包 -> Given NAS 发布包不包含 docker-build-context, When deploy-release 从 NAS 拉取发布包, Then 仍能通过 manifest、镜像 tar、compose、runtime-env、required SQL 完成部署。`
- `GREEN: experience-preflight -> PASS，本任务只改本机构建脚本与测试，不执行真实服务器发布、远端写入、备份、恢复或回滚。`
- RED: `python -m pytest scripts\tests\test_release_package_slimming.py` -> FAIL，当前 `publish-int-ruoyi.ps1` 缺少 `Remove-ReleaseDockerBuildContextFromPackage`，也没有 `Release package still contains docker-build-context` 的 fail-fast 门禁。
- GREEN: `python -m pytest scripts\tests\test_release_package_slimming.py` -> PASS，2 passed；清理函数存在，调用早于 manifest 和 NAS 上传，残留 `docker-build-context` 会 fail fast。
- GREEN: `PowerShell Parser.ParseFile(ops\deploy\publish-int-ruoyi.ps1)` -> PASS，脚本语法解析无错误。
- GREEN: `validate_cicd_environment.py --evidence doc\tasks\20260618-shrink-release-package\ci-cd-evidence.md` -> PASS。
- GREEN: `final-status -> PASS`，构建脚本已在 manifest 生成前清理 `docker-build-context`；未改写已部署历史发布包。
- GREEN: `task-closeout-cleanup --mode preview/apply` -> PASS，无 delete、blocked、warnings。
