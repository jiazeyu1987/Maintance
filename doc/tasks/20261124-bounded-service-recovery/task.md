# 前后端有限自动恢复

## 目标与授权

用户同意前述“有限自动恢复”方案：连续健康失败确认、保存故障证据、重启对应前后端服务、恢复复查、超过上限停止并告警，发布/备份/恢复/人工停服期间不得自动拉起。本次授权默认本地代码实现与验证；不安装到远端、不重启正式服务。

前序任务 `20261124-ops-tool-priority-review` 已completed并提交da07ac5。

## Current Status

completed

## 里程碑

- [x] 建立任务文档、读取前序状态与经验索引。
- [x] 核对现有执行器、远端锁/维护标记、运行控制与测试入口，固定正式设计和BDD。
- [x] 独立worktree按RED → GREEN → REGRESSION实现并验证。
- [x] 提交实现、融合int_main、融合后验证、清理本任务worktree。
- [x] 独立提交最终任务记录并报告安装边界。

## 预期验证

真实本地隔离进程/HTTP与文件/锁测试验证连续失败、恢复、重启上限和通知记录；维护/发布/备份恢复保护、停服、身份漂移和并发不得误重启。复用现有执行链，不用mock成功替代真实集成证明。产品真实E2E如涉及页面按真实入口执行，本任务不为测试新增产品控件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；失败显式记录，未知状态禁止重启。
- 是否从根因和长期维护角度解决：是；与既有服务身份和维护互斥机制集成，持久化计数与证据，不创建绕过发布控制的独立重启通道。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- Trigger：服务自动恢复、维护互斥、隔离worktree开发及中文PowerShell。
- Preflight check：当前规则与前序任务已读；按索引读取worktree、服务器访问及相关运行控制门禁；先确认已有锁和状态源，再写BDD与失败测试。
- Blocker：无法证明维护/人工停服边界、运行身份不明、与并发任务冲突或必要验证不可执行时，不运行重启、不伪造通过。
- Verification：记录RED/GREEN/REGRESSION、实现提交、融合提交、融合后结果及worktree清理；中文严格UTF-8回读及git diff --check。
- Forbidden action：不操作远端，不启动会隐式访问远端的页面，不修改受保护配置/租户/媒体，不提交他人改动，不无限重启。
- Evidence：本任务execution-log.md及源代码/测试位置；高风险融合/清理前记录experience-preflight PASS。

## 正式设计与BDD

- 运行位置：服务器本机Linux常驻服务；独立于浏览器、业务容器和开发电脑。仅恢复已显式arm的当前容器/镜像，不部署、不更换镜像、不启动已停止容器。
- 保护：同时持有既有发布runtime-operation.lock与备份/覆盖恢复共享sourceLockPath；备份epoch策略固定数据库UUID。数据库read_only/super_read_only、后端maintenance、关键依赖健康、容器身份、启动宽限和人工pause任一未知即禁止重启。
- 状态：私有目录内原子持久化失败计数、窗口内重启次数、未确认重启、告警投递outbox和采集时间；崩溃重启不清零预算，不自动重放不确定操作。
- 通知：可配置受保护webhook，投递结果独立于故障状态；投递失败可见且有界重试，记录恢复事件。CLI status对陈旧心跳返回非健康。
- Given连续真实HTTP失败且依赖/维护门禁正常，When达到阈值，Then仅重启对应原容器并在宽限后复核。
- Given发布或备份恢复共享锁被占用，或数据库停写、maintenance、人工pause/容器停止，When监测循环运行，Then零重启且明确记录保护原因。
- Given恢复后又失败或监测进程重启，When窗口预算耗尽，Then不再重启并投递限额告警，不能因一次健康或重启daemon清零。
- Given重启返回结果未知、容器/镜像更换、时间回退或保护状态读取失败，When继续监测，Then阻断自动恢复并保留证据。
- Given故障和通知HTTP失败，When后续投递成功/业务恢复，Then真实保留失败attempt、成功投递与恢复事件，不伪造送达。
- Given人工pause已返回，When随后停服或重启daemon，Then持续禁止自动恢复；重新arm必须完整健康且显式给出原因。
- Given发布器使用公共operationLockRoot及attempts/JOB-*工作目录，When新操作完成或失败并释放锁，Then新台账使旧arm失效，不能只扫描公共根目录而漏过重试发布。

## 阶段验证

- 首轮14项真实集成PASS；补充故障证据、锁权限兼容、daemon互斥与只读SQL白名单均先取得预期RED。
- 第二轮22项真实Linux Docker/MySQL/HTTP集成PASS（200.319s），无跳过、无业务容器操作、无远端访问；仍在补公共锁下attempt台账的回归及使用文档。
- 最终必要组合52项PASS（231.628s），补充收紧后的维护单项PASS（21.791s）。旧备份额外套件2项失败已在da07ac5原始归档复现，独立记录，不宣称旧备份回归通过。
- 实现提交43ee6e7，8个文件；融合前主线同路径冲突0，允许ff-only融合，正在主线复验与清理。
- int_main已fast-forward至43ee6e7，主线组合52项再次PASS（247.778s）。必要实现及验证完成，等待本任务工作区与隔离测试资源清理后才completed。

## 最终结果

- 实现提交：43ee6e7dba8d72429df936fd6779cebc577fdbba，已融合int_main。
- 必要验证：新增26项真实Linux Docker/MySQL/HTTP用例与相邻26项组合，分支52PASS（231.628s）、主线52PASS（247.778s），无跳过；严格UTF-8回读、AST/JSON解析、定向Git差异检查通过。
- 额外验证边界：旧recovery_minimal23项中2项既有失败在da07ac5原始归档同样复现；不纳入本次PASS、不修改旧备份模块。本次正式控制器复用的标准库epoch门禁已通过真实集成验证。
- 清理：官方integration_worktree_cleanup.py核对5307个文件并安全删除本任务工作区，Git登记及物理目录均消失；本任务测试network/volume及临时归档已移除，未启动或改动运行控制台。归属与结果见worktree-closeout.json、resource-closeout.json。
- 无新服务源码仓库参与，未创建前后端源码分支；维护仓分支产生一个实现提交且已融合。构建命令：无应用构建；验证命令为execution-log记录的真实Linux unittest。最终任务记录独立于实现提交。
- 安装边界：只完成本地代码/模板/说明，未连接服务器、未启用远端自动恢复、未配置真实通知收件端。远端安装与故障演练按对应环境另行授权及核实配置。

## 隔离工作区

- Codex托管创建失败：git config filter discovery超时；未取得可用目录，未重复创建半成品。
- 实际工作区：`C:/Users/D01021/Documents/ChatGPT/Maintance-worktrees/bounded-service-recovery`。
- 分支：`codex/bounded-service-recovery`；基线：`da07ac5a40c5cd397528636a056eb73764c93c9f`；完整checkout且初始git status为空，无端口或应用运行实例。
- 测试依赖：工具发现的Python3.12.14；本机Docker Linux可用，已有python:3.12-bookworm及mysql:8.0.39镜像；使用任务自有网络/卷/容器做真实集成，不触碰现有业务容器。
