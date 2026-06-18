# CI/CD 证据: 缩小 code-only 发布包

## Environment

- 目标脚本：`ops/deploy/publish-int-ruoyi.ps1`。
- 目标模式：`build-release`。
- 目标范围：未来构建发布包时，最终发布目录和 NAS 发布包不再包含 `docker-build-context`。
- 本任务不执行真实服务器发布、远端写入、备份、恢复或回滚。

## Commands

- RED：`python -m pytest scripts\tests\test_release_package_slimming.py`。
- GREEN：`python -m pytest scripts\tests\test_release_package_slimming.py`。
- PowerShell 解析：`[System.Management.Automation.Language.Parser]::ParseFile(...)`。
- CI/CD evidence 校验：`validate_cicd_environment.py --evidence doc\tasks\20260618-shrink-release-package\ci-cd-evidence.md`。

## Secrets

- 未新增或提交任何密钥。
- 本任务不读取或输出 NAS、数据库、服务器明文凭据。

## Pipeline

- 原流程：准备 `docker-build-context` -> 构建镜像 -> `docker save` -> 写 runtime env / compose -> 写 manifest -> 上传发布包。
- 新流程：准备 `docker-build-context` -> 构建镜像 -> `docker save` -> 写 runtime env / compose -> 删除 `docker-build-context` 并 fail-fast 校验 -> 写 manifest -> 上传发布包。
- 因为清理发生在 manifest 生成前，`release-manifest.json` 与 Manifest v1 都不会列出 `docker-build-context`。

## Verification

- `test_release_package_slimming.py` 覆盖清理函数存在、清理调用发生在 manifest/upload 前、残留目录会触发 fail-fast。
- PowerShell 解析通过，说明脚本语法有效。
- 未实际重建或改写已部署发布包，避免破坏已经用于测试服/备份服发布的历史 manifest 审计一致性。

## Rollback

- 如需回退，只需移除 `Remove-ReleaseDockerBuildContextFromPackage` 函数与 build-release 中的调用，并删除对应测试。
- 已生成的旧发布包不受本次代码提交影响。

## Blockers

- 当前无阻塞。
