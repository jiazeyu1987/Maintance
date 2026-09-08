# 发布流水线 P0 加固 PRD

- Task ID: `release-pipeline-hardening-20260907`
- Created: `2026-09-07T21:07:40+08:00`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiWorktrees\release-pipeline-hardening-20260907\m`
- User Request: `优化发布流程，使同一个安装包先发布测试服，验证后原样晋级正式服和备份服，并尽量减少服务器阶段才暴露错误导致的重复打包。`

## Goal

建立当前发布链路的 P0 长期安全基线：测试、正式和备份环境只能消费已构建的不可变发布包；生产级环境只能消费 `code-only` 包；每次使用包前都重新核对全部不可变文件；“已测试”证明必须绑定同一个包、同一份 manifest 和一次真实成功的测试服发布操作。任何缺失、篡改或绑定错误均在服务器写入前明确失败。

目标流程固定为 `build-release -> publish-test -> mark-release-tested -> promote-prod -> promote-backup`，全程使用同一 `releaseTag` 和同一 payload，不在环境之间重新构建。

## BDD Scenarios

### BDD-1：部署只能来自安装包

- Given：操作者准备部署任一环境。
- When：未显式提供合法 Mode，或尝试历史 `direct` Mode。
- Then：脚本在构建、NAS、SSH、Docker、数据库及文件写入前失败。

### BDD-2：生产级环境拒绝数据快照包

- Given：完整包的 `publishScope=with-data`。
- When：部署目标为 `prod` 或 `backup`。
- Then：本地校验后立即拒绝，不连接目标服务器；同一包仍允许按既有契约部署 `test`。

### BDD-3：篡改包不能使用

- Given：包中任一不可变文件被修改、删除、增加，或 manifest 的路径、长度、哈希声明错误。
- When：执行 build 入库、deploy 或 mark-tested。
- Then：逐文件校验报告具体相对路径和原因并失败，后续写入不执行。

### BDD-4：测试证明来自真实成功操作

- Given：包完整，但不存在同 releaseTag 的 `environment=test`、`action=publish-test`、`status=SUCCESS` 操作。
- When：执行 mark-release-tested。
- Then：不创建或覆盖 `tested.json`；失败、运行中、错误动作、错误环境或错误 tag 的记录均不能作为证明。

### BDD-5：同一已验证包晋级两个生产级环境

- Given：完整 `code-only` 包的 tested 证明绑定当前 package digest、manifest digest 和成功 publish-test operation ID。
- When：分别执行 promote-prod 和 promote-backup。
- Then：两个入口执行同一套强校验，校验后才进入既有生产确认、dry-run 与部署；备份服不再临时跳过 tested。

## Scope

- `ops/deploy/publish-int-ruoyi.ps1` 的 Mode、包生成/复制、部署前、mark-tested 和晋级门禁。
- 可新增 `ops/release/lib/ReleasePackageGovernance.psm1`，集中可独立测试的完整性、摘要、scope 与 attestation 规则。
- `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationAction.java`、`RuntimeControlService.java`、`RuntimeControlOperationStore.java` 的发布操作证据选择和命令参数。
- 对应 Java 测试与 `scripts/tests/` 本地合同测试。
- 保持合法 code-only build、test、prod、backup 既有参数及部署后健康检查兼容。

## Non-Goals

- 不连接或写入测试服、正式服、备份服、NAS、数据库和 MinIO，不执行真实构建发布、备份、恢复或重启。
- 不将 NAS 目录包改为 `tar.zst`，不实现签名、SBOM、全量离线依赖、NAS staging 原子入库或大脚本整体拆分。
- 不统一 legacy `release-manifest.json` 与 Manifest v1 `manifest.json`；本轮明确逐文件权威并将另一 manifest 纳入不可变 payload。
- 不改变 required SQL、迁移、OnlyOffice、展厅、健康检查和回滚业务语义。
- 不实现目标服务器 schema、磁盘、Docker、端口、备份点等真实只读 preflight。
- 不改变 Maven/pnpm/Docker 缓存策略。现有 Docker 应用镜像仍使用 `--no-cache`；没有输入指纹、失效规则和集成测试前，缓存优化作为独立后续任务。
- 不增加 fallback、mock 成功、兼容旧 tested.json 的放行分支、可选弱校验开关或手工绕过参数。

## Preconditions

- 仅在本任务 worktree 修改；重叠且归属不明的改动必须阻塞。
- Windows PowerShell 5.1、Python 3.12、pytest、Git、JDK 17、Maven 可用；缺少必需工具即 fail fast。
- PowerShell 文件必须通过 AST 解析；中文按 UTF-8 读写。
- 测试只使用 `$env:TEMP` 下无秘密 fixture，不读取真实本地运行配置，不调用真实 NAS/服务器。
- 生产代码修改前，`execution-log.md` 先记录 BDD 与 RED；各阶段严格 `RED -> GREEN -> REGRESSION`。

## Impacted Areas

- Mode 契约：删除 `direct` 和默认 Mode。
- 包契约：`release-manifest.json.artifacts` 是本轮不可变 payload 的逐文件权威，`manifest.json` 必须被声明。
- tested/rollback compatibility 是构建后受控证明文件，不计入 payload digest，但须独立验证。
- mark-tested 由服务端解析真实 operation，不能信任客户端 operation ID/status/path。
- prod/backup 不再依赖可省略的 `-RequireTested`，而由目标环境无条件要求 tested。
- scope、hash、tested 门禁必须早于 SSH、远端环境读取/写入、目录准备、Docker、数据库和 MinIO。

## Package Integrity Contract

- `release-manifest.json.artifacts` 每项包含规范相对路径、小写 64 位 SHA-256、非负 bytes。
- artifact 集合必须恰好等于包内除 `release-manifest.json` 及受控可变 metadata 白名单外的普通文件；白名单仅含 `tested.json`、`rollback-compatibility.json`、`prod-latest.json`、`backup-latest.json`、`prod-deployments/**`、`backup-deployments/**`。拒绝白名单外的额外文件，以及缺失、重复/大小写冲突、绝对路径和 `..` 路径。白名单文件被排除在不可变 payload 外不代表其有效：`tested.json` 由 P3 验证，deployment history 保持现有候选与回滚合同。
- `manifest.json` 是不可变 payload，必须出现在 artifact 清单并校验实际内容。
- `manifestDigest` 是 `release-manifest.json` 原始字节的 SHA-256，格式 `sha256:<64 lowercase hex>`。
- `packageDigest` 对规范记录求 SHA-256：第一条是 manifestDigest，其后按 ordinal 相对路径排序，记录每个已验证 artifact 的 path、实际 sha256、bytes。字段分隔与换行必须固定并由测试向量锁定，不依赖 JSON 属性顺序、绝对根目录或本机路径分隔符。
- build 本地完成后、NAS 复制完成后、deploy 下载后、mark-tested 写证明前调用同一校验器。调用者只能使用校验器返回的 releaseTag、publishScope、manifestDigest、packageDigest。
- `tested.json` 至少包含 schemaVersion、releaseTag、packageDirectoryName、packageDigest、manifestDigest、testEnvironment=`test`、publishTestOperationId、publishTestOperationStatus=`SUCCESS`、publishTestRequestedAt、testedAt、testedBy、testConclusion。时间为 UTC ISO-8601，digest 格式同上。
- tested 通过同目录临时文件原子替换；任何前置失败不创建、不截断、不覆盖已有证明。

## Phase Plan

### P1: 收口部署入口与生产级 scope

- Objective：禁用 direct，并在远端动作前阻断 with-data 晋级 prod/backup。
- Owned paths：发布脚本、可选治理模块、发布治理合同测试、现有 Java 参数合同测试。
- Dependencies：无。
- Deliverables：显式 Mode；test/prod/backup scope 决策；执行顺序合同；BDD/RED/GREEN 证据。

### P2: 建立逐文件完整性与稳定摘要

- Objective：构建、NAS 入库、deploy、mark-tested 共用严格校验和摘要算法。
- Owned paths：发布脚本、治理模块、`scripts/tests/test_release_package_governance.py`、相关 manifest/瘦身测试。
- Dependencies：P1 完成。
- Deliverables：正确 manifest 生成顺序；完整性/摘要实现；四个生命周期位置强制调用；篡改/缺失/额外/非法路径测试。

### P3: 绑定真实测试操作并统一晋级门禁

- Objective：服务端选择真实成功 publish-test，生成强绑定 tested，并让 prod/backup 使用同一无条件门禁。
- Owned paths：发布脚本、治理模块、RuntimeControl operation action/service/store、Java/脚本测试。
- Dependencies：P2 digest 已稳定。
- Deliverables：服务端 operation 解析；PowerShell 二次验证；tested 原子写入；prod/backup 一致校验；移除 backup 临时门禁和 RequireTested 绕过。

## Phase Acceptance Criteria

### P1

- P1-AC1: `direct` 不在 ValidateSet 且 Mode 无默认并为 mandatory；`-Mode direct` 与缺失 Mode 非零退出，失败前无副作用。
- P1-AC2: 经验证的 with-data 包对 prod、backup 明确失败，对 test 保持允许。
- P1-AC3: scope 判断发生在任何 SSH、远端环境、目录、Docker、数据库、MinIO 动作前，测试锁定顺序。
- P1-AC4: 控制台仍只生成显式 build-release、deploy-release、mark-tested；合法 code-only test/prod/backup 参数合同通过。
- Evidence expectation：execution-log 记录 P1 BDD、RED/GREEN、AST、pytest/Java 结果及 P1-AC1..4。

### P2

- P2-AC1: artifact 清单与不可变 payload 一一对应并包含 manifest.json；路径、bytes、hash 全部实算通过。
- P2-AC2: 同内容在不同绝对根和路径分隔下 packageDigest 相同；任一 payload/manifest 变化改变摘要或失败。
- P2-AC3: 篡改、缺失、额外文件、错误 bytes/hash、重复/大小写冲突、绝对/`..` 路径均非零失败并指出路径和原因。
- P2-AC4: build 在 NAS 前验证本地且复制后验证 NAS；deploy 下载后且远端动作前验证；mark-tested 写入前验证；失败不继续。
- P2-AC5: 不可变 payload 只排除受控可变 metadata 白名单 `tested.json`、`rollback-compatibility.json`、`prod-latest.json`、`backup-latest.json`、`prod-deployments/**`、`backup-deployments/**`；其他额外文件失败。排除不代表 metadata 有效，tested 由 P3 验证，deployment history 保持现有候选与回滚合同。
- Evidence expectation：execution-log 记录固定摘要向量、全部负例、调用顺序、AST、回归及 P2-AC1..5。

### P3

- P3-AC1: 只接受 operation store 中 environment=test、action=publish-test、status=SUCCESS、parameters.releaseTag 完全相同的操作；其他情况阻断。
- P3-AC2: 客户端不能提交/覆盖 operation ID、status、证据路径；它们由服务端选择，PowerShell 再读取 operation JSON 交叉验证。
- P3-AC3: tested 字段、格式、digest 绑定正确并原子替换；前置失败保持已有文件字节不变。
- P3-AC4: prod、backup 都重算 payload/package/manifest digest 并核对 tested 的 tag、目录、digest、test 环境、operation ID/status；任何陈旧或伪造值在远端写前失败。
- P3-AC5: 删除 `TEMPORARY_BACKUP_RECOVERY_GATE_DISABLED` 和 `RequireTested` 放行语义；两个生产级环境按 Environment 无条件要求 tested。
- P3-AC6: 合法 code-only + 成功 operation fixture 可完成 mark、prod gate、backup gate；全量本地 Java/Python/AST 回归通过且无外部连接。
- Evidence expectation：execution-log 记录全部 operation/attestation 正负例、Java 回归、无外部访问证明及 P3-AC1..6。

## Done Definition

- P1-P3 和全部 AC 完成并有 execution-log、独立 test-report 证据。
- 所有代码变化有 RED/GREEN/REGRESSION；必需测试无相关 skip/xfail。
- PowerShell AST、定向/全量 pytest、后端 Maven、`scripts/verify_contracts.py`、`git diff --check` 全通过。
- 独立 tester 使用 blind-first-pass，最终 verdict=PASS。
- 所有拒绝均在远端写入前；本任务无真实 NAS/服务器连接。
- 无秘密、fallback、降级、兼容旧 attestation 的放行路径。

## Blocking Conditions

- 必须连接真实环境才能证明本地门禁、缺少必需工具/依赖、测试失败、并发改动冲突时停止。
- 无法形成无循环的精确 payload 清单时停止，不得退化为只检查 hash 字段存在。
- 发现调用者仍依赖 direct 且无法在范围内迁移时列出并阻塞，不保留隐藏兼容入口。
- operation store 字段不足以证明成功 publish-test 时阻塞，不信任客户端补值。

## Follow-Up Work

- 单一归档、外部摘要/签名、NAS staging 校验和原子 READY 入库。
- 绑定 packageDigest 的服务器只读 preflight（schema、迁移、磁盘、Docker、端口、备份/回滚点）。
- 输入指纹驱动的 Maven/pnpm/Docker 缓存；先证明正确失效，再移除 `--no-cache`。
- 合并双 manifest 并拆分 builder/verifier/deployer/attestor。
