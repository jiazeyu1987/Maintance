# 任务: 缩小 code-only 发布包

## 任务目标

实现低风险发布包缩小：构建发布包时只保留部署必需内容，最终发布目录和上传到 NAS 的发布包不再包含 `docker-build-context`。

## 经验门禁

- `docs/release-build-preflight-lessons.md`：发布包必须以 manifest 和包内 artifact 为准；构建脚本或 script 变更提交前需要 TDD 证据。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布包必须保留 manifest、artifact、schema/required SQL 契约，不得用 mock/default success 掩盖失败；`code-only` 不包含数据同步，但仍要保留 required SQL 与发布 manifest。
- `docs/agent-memory/project-error-prevention.md`：发布流程变更提交前必须跑 TDD 钩子；失败不生成可部署包。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。若清理后缺少镜像 tar、manifest、required SQL、ops runtime 或部署所需文件，构建应失败。
- `是否从根因和长期维护角度解决`：是。移除最终包中的构建中间目录，而不是事后手工删除某个 releaseTag。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 构建发布包清理构建上下文 -> Given build-release 已完成 Docker 镜像打包和 manifest 生成, When 发布包复制到 NAS 前进行最终瘦身, Then 发布目录不包含 docker-build-context，且 manifest、release-manifest、镜像 tar、required-sql、ops-runtime 等部署必需内容仍存在。`
- `BDD: 部署仍可读取发布包 -> Given NAS 发布包不包含 docker-build-context, When deploy-release 从 NAS 拉取发布包, Then 仍能通过 manifest、镜像 tar、compose、runtime-env、required SQL 完成部署。`

## 里程碑

- [x] 创建任务文档并读取经验门禁。
- [x] 增加失败测试覆盖最终包不包含 `docker-build-context`。
- [x] 修改构建脚本在上传前清理构建上下文。
- [x] 运行受影响测试与发布脚本静态/单元验证。
- [x] 更新证据、收尾清理并提交。

## 预期验证

- RED 测试先证明当前脚本缺少最终瘦身门禁。
- GREEN 测试证明脚本包含上传前清理 `docker-build-context` 的步骤。
- `validate_cicd_environment.py` 通过。
- 不执行真实服务器发布或远端写入。

## 当前状态

completed

## Current Status

completed

## 实现记录

- 新增 `scripts/tests/test_release_package_slimming.py`，验证 build-release 最终发布包必须清理 `docker-build-context`，且清理调用早于 manifest 生成和 NAS 上传。
- 修改 `ops/deploy/publish-int-ruoyi.ps1`，新增 `Remove-ReleaseDockerBuildContextFromPackage`；该函数删除 `docker-build-context` 后立即回读校验，若目录仍存在则 fail fast。
- 清理调用放在 `Write-ReleaseManifest -PackageTag $ReleaseTag` 之前，因此 `release-manifest.json` 和 Manifest v1 均不会记录构建上下文。
- 未改写已部署的 `release-20260618-0056-codeonly-e2e` 历史发布包，避免 manifest 与已发布审计记录不一致。

## 当前验证

- RED：`python -m pytest scripts\tests\test_release_package_slimming.py` 失败，原因是旧脚本缺少清理函数和残留目录门禁。
- GREEN：`python -m pytest scripts\tests\test_release_package_slimming.py` 通过，2 passed。
- PowerShell 解析：`powershell_parse=PASS`。
- CI/CD evidence：`validate_cicd_environment.py --evidence doc/tasks/20260618-shrink-release-package/ci-cd-evidence.md` 通过。
- 预期效果：后续构建的 code-only 发布包会去掉约 `609 MiB` 的 `docker-build-context`，以本次 `release-20260618-0056-codeonly-e2e` 结构估算约从 `1,392 MiB` 降至 `783 MiB`。

## Cleanup Keep

- `doc/tasks/20260618-shrink-release-package/ci-cd-evidence.md`
