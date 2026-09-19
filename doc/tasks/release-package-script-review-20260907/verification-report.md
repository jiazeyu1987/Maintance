# 发布安装包与测试/正式服脚本审查报告

## 结论

用户提出的方向正确，目标应定义为 `build once, deploy many`：同一份内容不可变的发布包先部署测试服，测试通过后原封不动晋级正式服和备份服，环境差异仅由目标环境配置与秘密注入。

当前实现已经具备 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup` 骨架、releaseTag、NAS 发布包、manifest、目标环境配置和发布后健康检查，因此不是推倒重来。但当前发布包仍是 NAS 目录，不是一个强校验、原子发布、可独立验真的安装制品；若按“只要有包就能发布”理解，尚未达标。

## Findings

### P0-1 仍保留绕过安装包的 direct 发布路径

- `ops/deploy/publish-int-ruoyi.ps1:3` 默认 `Mode=direct`。
- direct 路径会从当前工作区重新构建并直接部署，绕过 NAS 不可变包、tested 门禁和正式服 dry-run 的完整链路。
- 建议：默认 Mode 改为无效并强制显式动作；生产可用入口只保留 `build-release`、`deploy-release`、`mark-tested`，禁用 direct 对 test/prod/backup 的写入。

### P0-2 with-data 包可进入正式服并具有覆盖生产数据能力

- `RuntimeControlOperationAction` 允许构建 `with-data`，正式晋级未限制只接受 `code-only`。
- `publish-int-ruoyi.ps1:6085` 的 with-data 部署会重建远端 MySQL 数据目录并导入本机构建时 dump，同时同步 MinIO 快照。
- `rollback-compatibility.json` 即使计算为 `BLOCKED`，`tested.json` 仍会写入；正式发布只检查 tested 文件存在。
- 建议：正式服和备份服默认只允许 code-only 包；数据库变化只允许幂等、可审计迁移。数据快照包应定义为独立 packageType，并限定目标环境与恢复用途，不能与普通应用安装包共用晋级规则。

### P0-3 部署前没有强制重算并验证整包完整性

- NAS 候选只判断 `release-manifest.json` 中存在 artifact sha256；`hasReleasePackageChecksum` 不验证实际文件内容。
- `Copy-ReleasePackageFromNas` 下载目录后未重算全部文件哈希。
- Manifest v1 验证仅在 `EnableSmartReleaseReport` 开启时以 report-only 方式运行，不是所有部署的阻断门禁。
- 建议：上传前、NAS 入库后、每次部署前都强制验证同一包摘要和所有文件哈希；校验失败必须在任何远端写入前停止。最好使用单一归档文件加外部 SHA-256，并对 manifest 做签名。

### P0-4 测试通过标记没有与“这一个包的真实测试结果”强绑定

- `Mark-NasReleaseTested` 只要求结论文本和恢复集字段非空，不证明同 releaseTag 存在成功的 publish-test operation。
- `Assert-NasReleaseTested` 只检查 `tested.json` 存在，不校验内容、manifest 摘要、测试环境、操作 ID或兼容性状态。
- 备份服路径还包含 `TEMPORARY_BACKUP_RECOVERY_GATE_DISABLED` 特例。
- 建议：tested attestation 必须绑定 package digest、manifest digest、测试服成功 operation ID、测试时间、验收项和操作者；正式/备份晋级时重新验证全部绑定字段。移除临时禁用门禁。

### P1-1 NAS 发布包上传不是原子操作

- `Copy-ReleasePackageToNas` 直接把目录复制到最终候选路径。
- 大镜像复制过程中，候选扫描可能看见不完整目录；若 manifest 较早出现，可能被误判为可用。
- 建议：先写入 `<releaseTag>.uploading/<uuid>`，完整校验后再原子重命名为最终目录，并写入不可变 `READY` 证明；最终目录禁止覆盖。

### P1-2 包仍依赖外部镜像且存在漂移版本

- 镜像 tar 只包含本次应用镜像和可选 OnlyOffice；MySQL、Redis 与远端 smoke 所需镜像不在包内。
- `onlyoffice/documentserver:latest` 未固定版本或 digest。
- 建议：明确两种正式契约之一：一是“应用发布包 + 已验证平台基线”，包中记录并校验所有外部镜像 digest；二是“离线全量安装包”，将全部依赖镜像纳入归档。无论哪种都禁止 `latest`。

### P1-3 构建只记录 dirty，没有阻断 dirty 源码入包

- `New-ReleaseSourceRepoEntry` 记录 `dirty` 与摘要，但不 fail fast。
- 建议：build-release 必须要求所有参与仓库处于专用 release worktree、HEAD 已提交且 `dirty=false`；manifest 记录精确 commit，构建后再次核对 HEAD 未漂移。

### P2-1 发布实现过于集中且存在双 manifest 契约

- `publish-int-ruoyi.ps1` 当前约 6230 行，同时承担构建、打包、NAS、迁移、部署、验证和测试标记。
- 部署主流程仍依赖 `release-manifest.json`，而较完整的 `manifest.json` 主要用于可选 Smart Release 报告。
- 建议：保留一个权威 manifest，拆分为 package builder、package verifier、environment deployer、promotion attestor 四个模块；入口脚本只编排，不重复定义契约。

## 目标安装包契约

建议最终只有一个不可变制品，例如 `release-<tag>.tar.zst`，配套一个外部摘要/签名。包内至少包含：

- 单一 `manifest.json`：releaseTag、package digest、源码 commit、dirty=false、packageType、allowedTargets、构建工具版本、所有文件哈希。
- 固定 digest 的应用镜像；若选择离线全量包，则同时包含全部基础设施镜像。
- docker compose 模板和迁移脚本，不包含服务器 IP、密码、token 或环境秘密。
- preflight、verify、rollback 计划，以及数据库迁移的前置条件和不可逆标记。
- SBOM/依赖清单、构建日志摘要和测试报告摘要。

“打包时考虑各种可能性”不能替代目标环境检查。正确拆分是：打包时证明制品自身完整、可重复、无秘密、迁移静态合法；部署前再证明目标服务器容量、Docker/镜像基线、当前 schema、备份/回滚点、环境秘密、端口和健康条件满足。两类门禁都通过才允许写入。

## 推荐实施顺序

1. 第一阶段只做 P0：禁用 direct 写入、禁止 with-data 晋级正式/备份、强制整包哈希校验、tested 与真实测试 operation/包摘要绑定、移除备份服临时门禁。
2. 第二阶段把 NAS 目录收敛为单一归档制品，改为 staging 校验后原子入库，并统一 manifest。
3. 第三阶段固定全部外部镜像 digest，明确“平台基线包”或“离线全量包”策略，再拆分 6230 行脚本。
4. 用户界面最终只保留四个顺序动作：构建安装包、发布测试服、确认测试通过、晋级正式服；同一安装包内容在整个流程中不得变化。

## Verification Boundary

- 本次仅静态读取当前工作区脚本、Java 编排、合同测试与发布规范。
- 未执行构建、测试、NAS 写入、服务器连接、发布、备份、恢复、重启或数据库操作。
- 当前工作区存在其他任务的未提交改动；本报告未修改、覆盖或评价其归属。
