# Spug 按次选择恢复服务器

## Current Status
blocked

本轮已授权的组件安装及本地接入已完成；测试服、备份服已启用。原需求“三服均可作为目的地”仍缺正式服稳定运行身份前提，正式目标准入保持阻塞。保留本任务开发 worktree 续作；两个临时发布 worktree 已删除，无待收尾发布目录。没有执行数据恢复。

## 用户需求与授权
用户要求在 Spug 按次选择测试服 .58、正式服 .57、备份服 .59，后续正式来源的新备份自动发现。已授权三服只读检查，并明确“允许安装控制组件和登记配置，不执行恢复”；正式服前置不通过时不启用。用户确认所列 EDHR MinIO 账号“仅供 IntRuoyi 主程序使用”。授权不包含业务/数据库/MinIO/Redis停启、实际恢复或正式服业务异常修复。

前一自有任务 20261104-restore-target-label-explanation 已 completed。本任务工作区为 C:/Users/D01021/.codex/worktrees/spug-restore-targets/Maintance，分支 codex/spug-selectable-restore-targets-20261104，base 9a62391。固定 E: 文档路径不存在，已使用 C:/SpugHandoff/release/repository/docs/ 现存权威规则副本；未伪造固定目录。

## 里程碑与预期验证
1. [x] 只读核对当前 Spug、真实主实例、资源归属、程序与存储合同；开发隔离及任务文档先行。
2. [x] BDD + RED/GREEN/REGRESSION：主实例严格身份与存储 v2、动态原备份链、所选目标预检、显式接口能力；重构使用已委派子代理。
3. [x] 仅从已提交快照在专用临时发布 worktree 构建；三服各 121 程序文件 SHA256 读回一致。
4. [x] .58/.59 目标配置、认证控制服务、本机18080 Spug定向接入及稳定自动重连通道安装完成。
5. [x] Playwright 真实登录后分别选择 .58/.59，打开覆盖确认并返回修改；精确目标绑定，恢复提交为零；正式服保持禁用。
6. [x] 实现 e1389aa 合入 int_main，合并结果相关回归通过；两个干净临时发布 worktree 的注册与物理目录均已删除。
7. [ ] 正式服 .57 稳定身份与完整资源前置通过后再登记启用。当前不具备该前提，禁止伪造可恢复或越权修复主程序。

## 经验门禁
- Trigger：Spug 备份恢复、主实例覆盖目标登记、真实页面验收和隔离 worktree 收尾。
- Preflight check：先核实际18080挂载和版本、用户授权、目标实际Docker/配置/版本/网络/数据归属、共同锁、NAS归档链及全部pin；高风险阶段先在 execution-log.md 记录 experience-preflight PASS。规则按 docs/experience-index.md 路由至发布恢复、PowerShell及worktree资料。
- Blocker：实际身份不可核验、writer归属不明、独占资源/锁/版本/存储/pin不符、接口或认证不可达，均停止对应目标；正式服当前命中精确 backend inspect 超时。
- Verification：相关合同、真实Linux文件系统检查、认证selected-target准入、原始包编号/祖先链、页面确认/取消、零operation/claim、业务启动时间不变、融合后验证与目录物理清理分别留证。
- Forbidden action：禁止复制freshRef充当覆盖目标、仅解禁按钮、跳过预检、静默降级、伪造writer/成功；不改业务容器、共享NAS/fstab、受保护展厅配置、芋道源码租户及并发任务资产。
- Evidence：execution-log.md、两个子任务日志、installation-status.json、browser-choice.json、implementation-integration.json、release-worktree-cleanup.json；凭据和完整运行配置仅存私密目录。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。旧控制接口通过显式 selectedTargetPreflight 能力保持原合同；没有失败重试到其他目标。
- 是否从根因和长期维护角度解决：是。真实主实例运行合同、精确存储v2、动态备份目录及按所选目标核验，保持原七字段恢复请求与不可变目标。
- 是否存在临时补丁或绕过：否。Docker local bind的真实底层路径显式登记，不猜测或改Docker定义；nsfs仅按真实类型解析。通道有互斥和断线重连，稳定目录独立于开发及发布checkout。

## 最终安装状态与限制
| 服务器 | 当前结果 | 证据与后续 |
| --- | --- | --- |
| .58 测试服 | 覆盖目标已启用，控制服务active，所选目标准入通过 | intruoyi-main-58-safe-restore-20261104-v1；loopback控制43658；operation=0、claim=0 |
| .59 备份服 | 覆盖目标已启用，控制服务active，所选目标准入通过 | intruoyi-main-59-safe-restore-20261104-v1；loopback控制33659；operation=0、claim=0 |
| .57 正式服 | 仅程序组件stage，目标禁用，无新控制服务 | 最新只读load约1553，精确backend inspect 4秒超时；稳定身份与资源合同无法完成。未证实高负载根因，未做业务修复 |

两服所有业务容器StartedAt与安装前一致；实际IAM账号/策略摘要绑定用户归属确认。所有者配置和执行前漂移检查仍生效。来源保持 intruoyi-57-safe-20261024-v1，真实4个有效点仍用原编号；后续新点按目录及祖先链动态解析，版本兼容/完整性/目标准入不通过仍明确拒绝。没有创建新备份或验证实际数据恢复，不能把选择/取消PASS说成恢复成功。

本地仅补adapter选择预检能力与两目标的simple/entry/bridge/progress登记，保留现有UI、其它来源、历史路由和独立18081实例。Windows三项当前用户登录计划任务均Running，稳定脚本 C:/Spug/runtime/private/restore-targets-20261104/restore_control_transport.ps1；服务器自有控制服务启用开机启动。未以重启机器验收启动项。没有依赖旧来源SSH进程或临时worktree。

## 构建、融合及清理记录
| 临时发布 checkout | 构建目标 | 是否产生新提交 | 融合及最终删除 |
| --- | --- | --- | --- |
| C:/Users/D01021/.codex/worktrees/spug-restore-install-20261104/Maintance | f36ff55a6588cb11822dd7611699a2ad76c7207b | 否 | 已为int_main祖先；clean且无路径引用进程；Git注册和物理checkout已移除 |
| C:/Users/D01021/.codex/worktrees/spug-restore-install-20261104-v2/Maintance | 08045c1起，核clean后本任务内迭代到45b4e3e4267183306dcc087e0c52659b6df5d463 | 否 | 同上；未跨任务复用 |

构建命令为 bundled Python -X utf8 ops/backup_engine/build_variants.py --output-directory <任务私密输出目录>；输入固定对应Git已提交内容。最终安全包SHA256 c9e7726f3024af04e92d53b53f9a30439d6b9f3ae2393615efed207961e0cdd2，文件清单摘要11d84d9a272e2048f242cd3f1e768940b25ed813cbfbb857ea2f8a0adbabe1d3。验证为git status --porcelain、manifest逐文件SHA、目标认证准入和真实页面取消。

实现提交 f36ff55、df9c3f8、08045c1、45b4e3e、3569e73、bc3b5c3、e1389aa 已fast-forward至int_main。融合保留主工作区1692项既有脏路径。合并结果Python合同137 PASS；Windows 7项POSIX检查已有相同提交实现的Linux98 PASS/0skip证据；Spug45 PASS、JS42 PASS。早期Linux综合234 PASS及主实例Windows/Linux各29 PASS保留历史日志，不替代后续补丁回归。

## 未解决阻塞及影响
正式服目标未启用，故目前只能把正式来源备份选到测试服或备份服；不能承诺恢复到全部三服。需要先取得正式服稳定、可核验的主实例身份及完整资源合同，再在授权范围内继续登记。当前安装授权不包含修复正式服业务运行异常。本轮控制组件安装结果与原需求尚未达成部分分别保留，开发worktree不删除。
