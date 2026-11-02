# 三服最新代码发布方案

## Current Status
completed

## 任务目标
按用户要求编写可审查的三服发布方案。本任务仅编写文档，不构建、不发布、不操作远端、不更改业务数据。上一同链任务 `20261030-spug-handoff-install` 已 completed，安装验收为 PASS_WITH_FINDINGS；本方案必须继承其未关闭发现，不能把安装通过当作新发布通过。

### 2026-10-31 审阅修订范围
- 按用户七点审阅及 NAS 重传要求修订原方案，保留主流程；用户最新指令优先于旧 AGENTS/经验中的泛化规定。
- 不因 static-only 新增构建前结构演练或开发阻塞；依据实际生效配置核版本；区分持久精确路由已修复与 Docker 网段仍重叠；不重启/删除现用演练环境。
- 补齐 gxpConfigurationSourceUrl、仓库外真实登录凭据及已保存模式来源；确认本地实际为关闭，发布清单与三服发布后的实际模式均必须关闭。当前仅核对本机来源，未发布三服。
- 区分只读验收和真实写入功能回归；移除自动合并 int_main 及将 Git/清理泛化为发布成功条件；加入 NAS 已构建原包校验重传。
- 本次只修改文档并作必要的只读核对；不修改产品代码、业务数据或 GxP 开关，不执行发布、推送、合并或清理。

### 修订里程碑
- [x] 核对 GxP 来源/读取、模式随包下发及 NAS 原包重传的真实代码。
- [x] 修订方案与给另一台电脑的审阅反馈；旧经验门禁按最新指令收窄。
- [x] 本地 GxP 关闭状态如实核验、文档核对及收口；三服模式保留为发布时必验，未发布不签发通过。

### 修订经验门禁
- Trigger：本次方案审阅；Preflight check：以当前明确用户范围和实际执行器合同核对；Blocker：无法证明本地来源模式/包模式/部署模式为关闭或必要登录缺失；Verification：脱敏来源、实际页面、manifest 与部署后证据分开记录；Forbidden action：把 static-only 当缺陷新增开发、用无效 .env、重启网络或自动合并、假称三服已发布；Evidence：本次审阅、GxP 读取及运行态代码、修订执行记录。
- 旧经验中的构建前结构演练、自动 int_main 融合及强制 .env 项，按本次用户明确修正收窄；后续修订方案为当前执行依据，历史记录不改写成已运行证据。

## 里程碑
- [x] 核对经验索引、现有发布契约和安装验收发现。
- [x] 编写从目标提交冻结到三服推广与回滚的操作方案。
- [x] 核对文档、编码和变更范围，分别提交交付物与任务收口记录。

## 预期验证
文档须明确单一 releaseTag 全链路、最新代码定义、代码与私密状态边界、隔离 worktree、正式全量数据演练、真实 Playwright 登录、生效启动配置、GxP 来源及关闭一致性、失败停止、NAS 原包重传和按授权收尾。与固定代码及验收证据交叉核对；原版为纯文档，本轮另按用户要求对本地 GxP 作真实页面只读核验，不发布三服。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；依据实际生效配置、现行执行器合同与用户明确范围处理，不把 static-only、非生效旧文件或网络全面改造扩大为发布前开发门槛。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：三服发布方案；Preflight check：按经验索引定位发布、迁移、恢复、worktree 和真实 E2E 规则，并核对当前代码；Blocker：必需文档或契约缺失、目标版本不明确；Verification：逐阶段列证据与停止条件；Forbidden action：本任务执行构建、发布或远端写入；Evidence：execution-log.md 和交付方案。
- 继承门禁：源机单执行器、发布历史一致；原包只读保留；Git 仅更新代码；版本依据为实际生效启动配置/manifest/镜像一致，旧 .env 仅在真实被读取时适用，不造无效文件。
- Trigger：构建及跨环境晋级；Preflight check：冻结完整应用/维护提交、干净专用 worktree、实际脚本字节摘要、包/manifest 双摘要；Blocker：来源不明、脏输入、摘要或目标漂移；Verification：记录不可变包和各服独立验收；Forbidden action：重建已测包或拼不同 releaseTag；Evidence：release-agent-checklist.md、release-build-preflight-lessons.md 不可变包及执行器摘要门禁、固定维护代码。
- Trigger：迁移及真实目标数据；Preflight check：历史不可变、显式注册、依赖闭包和现行目标数据检查，后续正式完整数据演练；Blocker：现行合同的未知/失败迁移或数据检查不通过；Verification：静态计划、原始台账、正式演练编号与目标指纹分别记录；Forbidden action：改旧 SQL/ledger、冒称真实演练或仅凭 static-only 新增结构演练/开发；Evidence：用户本次审阅、当前 intruoyi_build.py 与执行器合同。
- Trigger：真实登录与业务验收；Preflight check：当前用户指定测试租户/账号、真实页面、私密凭据、实际入口；Blocker：租户未选中、权限/入口/基线缺失或登录失败；Verification：Playwright 登录后身份及版本、正式/审查独立业务结论；Forbidden action：接口冒充页面、改密码或权限、擅自业务写入；Evidence：test-release-preflight.md、当前发布中心 README 三项技术检查及验收代码。
- Trigger：远端写入、备份和恢复；Preflight check：当前任务环境授权、生产确认、互斥与原任务回执、writer/fence、实际恢复资源及一致性；Blocker：未知中断/写入状态、缺恢复点、共享资源归属不明；Verification：原任务、恢复点、恢复验收和开放状态；Forbidden action：自动重试部分迁移、开放后直接回灌旧数据、删除共享 NAS；Evidence：固定应用仓 release-backup-restore.md/server-access.md、维护恢复文档。
- Trigger：worktree/Git 收尾；Preflight check：明确本次操作范围、实际路径、归属和并发使用；Blocker：拟操作无授权或归属不明；Verification：发布结果与获准收尾分开记录；Forbidden action：自动合入 int_main、超范围推送/清理或把这些全部设为发布完成条件；Evidence：用户本次审阅优先于旧通用收尾规则。

## BDD / TDD 范围
Given 用户仅要求发布方案，When 编写并核对文档，Then 交付明确步骤、证据、阻塞与失败处置，且不触发任何发布。没有功能或行为变更，RED/GREEN 运行测试不适用。

## 首版完成与验证（历史）
- 交付物：release-plan.md，共 163 行；完整流程、现有阻塞及证据边界已写明。
- verification.json：11 项文档静态检查全部 PASS；UTF-8 无 BOM、引用路径、动作名称、必要提交、历史发现及启动命令核对通过。
- `git diff --check` 通过；未运行构建、运行测试、真实 E2E 或远端操作，没有变更运行控制台。
- 生产发布的既有发现仍列为将来执行前的阻塞；它们不阻塞本次文档交付。方案已单独提交为 `6594c8c`；最终任务记录单独提交。

## 首版收口结果（历史）
- 本任务没有创建临时 worktree，无需合并或删除，也没有任务进程和控制台需恢复；未触碰其他任务资源。
- 提交仅包含本任务文档与脱敏验证记录；工作区原有四项 tracked 修改保留，未推送远端。
- 最终验证结论：文档交付 PASS，实际三服发布未执行，现有发布前问题没有被改写为已解决。

## 修订已完成与验证
- 已将七项审阅、NAS 原包重传以及本地/manifest/隔离副本/三服关闭一致性写入 release-plan.md；第十节去掉自动融合及泛化收尾条件。
- 本地来源 URL 已配置为 http://127.0.0.1:8081；登录工具和私密文件存在，真实页面登录可用。已保存与当前运行均为 DEVELOPMENT_DISABLED，auditEnabled=false，pendingRestart=false，页面两项均显示关闭；不改配置、不重启。
- 两次严格浏览器脚本因自动 workbench/context POST 被保护拦截而整体 FAIL，保留原始 attempt1/attempt2；local-gxp-verification.json 仅归纳有原始响应、可见页面和截图支持的 GxP 关闭结论，不冒称整体 E2E 通过。
- 三服发布/模式验收未执行；方案按未来发布后逐服核验，不用本地结论代替。
- 本轮未修改产品代码、未新增开发门槛、未提交/推送/合并或清理 Git/worktree；不以这些操作作为文档交付前置条件。
- verification.review.json：用户修订条目、真实代码依据、UTF-8、敏感值未泄漏和原始浏览器失败保留等静态核对全部 PASS；方案 188 行，git diff --check 与核验脚本语法检查通过。原 verification.json 仅对应首版历史，不冒充当前版本验证。

## 修订收口
- 本次文档与本地 GxP 只读确认完成；三服发布与发布后 GxP 验收为 NOT_EXECUTED，未标成功。
- 本任务没有创建/删除 worktree，没有需要恢复的控制台或服务；浏览器已在 finally 关闭。其他任务和已有本地修改保留。
- 修订结果保留于工作区供审阅及另一台电脑交接，不自动提交、推送、合并或发送给未指定的目标。
