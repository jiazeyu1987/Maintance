# Request Analysis

## User Goal

用户已授权在现有发布体系上修改：每次交付完整程序包，保留各服务器业务数据；同一个不可变包和同一个执行器根据测试、正式、备份服务器各自状态生成升级计划，并可靠报告实际运行版本及失败状态。本次授权覆盖本地实现、测试和文档，不包含真实服务器发布、重启、迁移、恢复、清锁或数据修正。

长期方案采用现有制品治理、版本迁移、写入 fence 和应用工作流，统一它们之间的合同，不另建一套发布系统，也不以一次性补丁修正服务器现场。

## Current System

静态审查基线：维护仓 `3f3aabdc82ab5e85e2f872173a665a361f022725`，应用协调仓 `840b9ef`。实施使用维护仓当前 `int_main` 创建独立 worktree。主管已确定通过显式依赖任务复用提交 `772fc46` 中相关的已提交 P1 修复（15 个生产/测试路径，迁移 supersession/依赖与真实锁 SQL）；须先在当前主线保留 RED，再进行独立回归。不得导入 `d316da9` 的 input-preparation 改动或未完成的两入口 P2–P5 应用工作流/UI。

- `ops/deploy/publish-int-ruoyi.ps1` 是当前维护执行入口，模式为 `build-release / deploy-release / mark-tested`，环境为 `test / prod / backup`。标准 `app-release` 已禁止全量数据库和 MinIO 同步。
- `ops/release/lib/ReleasePackageGovernance.psm1` 已校验包文件、来源及 `packageDigest / manifestDigest`，正式和备份晋级依赖已绑定测试 operation 的证明。保留这些机制。
- `-Component` 仍接受 `full / intruoyi / backend / frontend / website`；部署允许显式参数覆盖 manifest。应用 `RuntimeControlOperationAction` 根据 `includeShowroomBuildPackage` 传入 `full` 或 `intruoyi`。这涉及外部 Website 产品，不能把其既有显式选项无说明地删除。
- 完整性校验只证明 manifest 中声明的文件未变，不能证明包包含全部安装输入。部署仍保留缺少 Compose 或展厅模板时使用维护工作区模板的分支。
- `Write-FinalDockerBuildEvidence` 已采集镜像 ID 并写入 `manifest/docker-build-evidence.json`。最终 `Assert-RemoteActualApplicationImages` 只比较容器 `.Config.Image` 标签，尚未核对容器 `.Image` 的不可变内容身份。
- `Write-ReleasePreflightPlan` 位于挂载准备、控制文件复制和部分 DDL 之后；读取迁移台账时只保留成功类状态。`release_preflight_plan.py` 会把已成功但摘要不同的历史迁移重新排为 `APPLY`，未把失败/运行中状态作为阻断条件。
- 部署主链在 `.env` 切换后执行容器重建和验收，异常路径主要将锁标为 `FAILED`。运行态、已完成迁移、零写入证据和恢复需求尚未形成一个可持久读取的底层回执。
- 应用层已有 `RECOVERY_REQUIRED`、`zeroWriteEvidence`、执行器 SHA 校验及两阶段发布授权。应连接底层事实，不另造一套互斥状态。
- 既有 `release_deployment_transaction.py` 是本地 JSON 文件模拟原语；其通过不能证明实际 Docker/MySQL 部署失败行为。

前序只读报告位于 `doc/tasks/20260925-three-server-package-portability/verification-report.md`。该报告记录的三服差异是风险输入，不是本任务已重新验证的现场事实，也不能作为授权修改三服的依据。

### Pending two-button integration interfaces

另一个任务拥有只读参考工作区 `D:/IntRuoyiWorktree/two-button-release-delivery-maintenance`（参考提交 `d316da9`）与 `D:/IntRuoyiWorktree/two-button-release-delivery-app`（参考提交 `46271a0c6`）。存在直接文件重叠，禁止整体替换、重置或合并其未提交内容。

| 接口 | 必须保留或显式协同的合同 |
|---|---|
| PowerShell 参数 | 三种模式、三个环境、来源提交/SourceSelectionId、包摘要、测试证明、正式 dry-run 参数及现有外部调用含义 |
| 包与测试证明 | releaseTag、packageDigest、manifestDigest、sourceRoles、tested v2 的来源绑定；新字段不能破坏既有摘要算法 |
| 应用派发 | RuntimeControlOperationAction 构建命令；includeShowroomBuildPackage 及组件集合必须在包构建时确定，晋级不能更改 |
| 两入口编排 | ReleaseWorkflowOrchestrator 的创建、测试、验收、晋级、授权、终态及恢复语义；不重新设计页面或按钮 |
| 迁移计划 | 并行分支新增 input preparation、supersedes、目标数据 preflight 和依赖顺序校验；本任务严格化失败/摘要状态时必须保持其已验证依赖语义 |
| 失败证据 | 现有 operation 日志/证据引用、RECOVERY_REQUIRED、zeroWriteEvidence 与租约；同一失败事实不能在不同层分别标为可重试和需恢复 |

## Constraints

- 一个包固定一套受管组件和迁移；不同目标仅注入自己的配置/秘密并执行各自待执行迁移，不重新编译或改包。
- IntRuoyi 核心程序集合必须包含 backend 和 frontend。保留构建时显式产品范围 `intruoyi` 和 `full`（额外含 Website），禁止 backend/frontend/website-only 标准 app-release；部署参数不能覆盖或缩窄包范围。Website/OnlyOffice 的纳入情况必须固定在 manifest 并明确记录；不随包交付的独立产品不能被错误宣称与全局 IMAGE_TAG 同版。
- 不清库、不导入源库覆盖目标、不覆盖对象存储，不创建空持久目录替代缺失挂载，不修改受保护展厅文件配置或审核矩阵。
- 不支持的旧基线、缺少控制表/列、历史迁移异常、缺少所需制品及依赖均 fail fast；不在常规安装中自动修复或清除它们。
- 只读预检发生在首次目标运行配置/持久数据写入前。获取持久锁属于明确的控制写入，必须在只读预检通过后；在锁内重采关键状态并比对，才进入业务/运行写入。
- BDD、RED、GREEN、REGRESSION 和独立验证必须使用实际实现，不能只检查源码字符串或测试复制的算法。测试不使用共享数据库或共享容器冒充隔离环境。
- 完成实现前不得声称三服可以成功升级。本次本地验收与后续真实三服发布验收是不同结论。
- 不因缺少 `origin` 阻止本地实现；推送和正式 Git 收尾限制单独记录，不杜撰远端或成功结果。

## Unknowns

1. 依赖任务需要列清 `772fc46` 的精确纳入文件和行为，并证明没有带入两入口未完成工作；其他任务的 worktree 不是本任务可写路径，其 P4/P5 未完成不构成本任务阻塞。
2. 主管已确认 Docker 29.2.1、MySQL 8.0.39 镜像、PowerShell 5.1/pwsh、Python、Node 可用；任务自有容器/数据卷/端口仍需在真实集成前确认归属和空闲，不能修改既有业务数据库。
3. 现有服务器旧控制表结构、失败迁移和异常锁能否满足新执行器前提，需要后续授权的只读/修复任务确定。本次不替它们编造可升级证据。
4. 宿主工具属于包载荷还是固定平台依赖，应在代码检查后逐项固定；缺少清晰归属的必需工具不能继续依赖偶然残留。
5. 故障恢复回执与现有持久部署门禁/应用工作流的最小连接点、回执持久目录和读取方式由开发计划冻结。优先维护仓实现；应用主线为只读合同消费者，只有出现具体必要改动才扩大写入范围。不得只写无人消费的 JSON 文件并宣称失败重试已受保护。
6. 维护仓 `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationAction.java` 实际存在且被 Git 跟踪，主工作区与本任务 worktree 均已确认。早期 `rg --files` 输出受忽略规则影响，不能据此判定文件不存在。它属于维护仓 legacy 调用方，需与实际应用调用方 `E:/IntRuoyi/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeControlOperationAction.java` 分别核对真实源码合同；禁止制造假源码或复制文件来让测试通过。

## Risks

- 收紧旧包/旧基线门禁会明确拒绝此前被允许的部署，这是数据保护的预期行为；文档应写明错误和正式准备路径，不增加兼容 fallback。
- MySQL DDL 不能整体回滚。迁移后失败仅能报告真实状态并保持写入保护；不得默认恢复旧镜像或恢复备份抹去新增业务。
- SSH 或进程突然中断时无法保证最终观测完整。阶段记录必须在可能写入前持久化；无法采集的字段显式为 unknown/error，而非沿用旧值标成功。
- 文件存在/标签一致不足以证明内容正确。必须把包内摘要、实际加载镜像和运行实例身份贯通。
- 重构核心脚本与并行两入口任务高度重叠。需任务隔离、显式依赖、合并后回归，不能因另一个任务尚未交付而悄悄删掉它的合同。

## Validation Surface

- 包治理行为测试：核心组件、必需控制文件、镜像身份、晋级覆盖参数、秘密/业务数据边界。
- 计划器行为测试：同包三种已定义起点、拓扑依赖、相同校验跳过、历史摘要差异、FAILED/RUNNING、缺失前提、状态指纹变更及包绑定。
- 实际 PowerShell 函数/生成命令合同：从只读预检到锁内复核到写入的顺序、只读路径无 mkdir/mount/DDL/Compose 覆写等写操作、持久数据不被初始化。
- 任务自有真实 MySQL/Docker 集成：合法旧基线升级与保留行数据、执行中异常、同标签不同 imageId、锁/回执保留。不得以真实三服作为单元测试环境。
- 现有应用工作流定向测试：失败写入证据进入恢复态，预检零运行写入失败不误报切换或成功；保留两入口 API/参数合同。
- 未新增或修改产品交互时不凭空增加 UI 工作。若必要改动影响页面既有行为，按项目规则补真实 Playwright 路径；找不到入口则报告，不添加测试专用控件。

## Blocking Prerequisites

进入实现前：冻结任务可写仓库/分支和明确的 P1 依赖纳入清单。完整产品范围已冻结为 intruoyi/full；已有本地引擎能力不等于已预留隔离资源。进入真实集成前：任务独占容器、数据卷和端口确实可用，使用实际生产函数/生成 SQL/SSH shell 验证关键行为。进入远端部署前：另有明确授权、目标真实基线通过预检和恢复要求满足；这些远端条件不要求在本次未经授权地执行。

已知 `origin` 缺失仅限制推送/最终收尾；NAS、三服现场锁或现有数据库漂移不阻止纯本地代码与单元验证，但不得因此声明远端晋级验收完成。
