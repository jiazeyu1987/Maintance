# 经 Spug 将正式备份恢复到备份服（审查服 .59）

## Current Status
completed

## 目标与授权边界
用户当前目标：“在Spug里操作，恢复到备份服，修复恢复过程中发现的问题，一次点击，恢复成功为目标达成”。备份服对应 172.30.30.59，现行服务器文档称审查服，按 PROD 等级处理。本次明确要求实际恢复，取代此前仅安装、原服务启动和选择取消验证的不执行恢复边界；允许按登记的原 MAIN 覆盖合同完成恢复所必需的停写、恢复及启动。不得操作正式服 .57 的目的地、重启整机/Docker、修改其它业务或清理共享 NAS。采用刚在测试服独立验收成功的正式来源 FULL；若当前已存在本目标操作，沿原句柄跟踪，不重复提交。

前一自有测试服恢复任务 20261104-spug-prod-full-to-test 已 completed，1e4b3d0 完成审计。原三服登记任务已明确 blocked 于 .57 目的地合同，其独立阻塞不改变本次真实 .59 恢复范围。本任务开始时.59只有原服务/准入/页面选择验证；本次新增真实恢复成功与恢复后业务页面证据，不沿用测试服成功代替。

## 里程碑
1. [x] 只读确认来源 FULL、.59 原实例/版本/存储合同与原始运行基线、活动操作及资源预约；核现行授权与规则。21:07 restore-preflight.json PASS，122程序文件摘要、归档6份pins、原目标运行/存储、认证准入通过；数据盘可用183289016320字节，无活动恢复或预约。实际停写/fence及写入前锁内核验由恢复器正式执行。
2. [x] 真实Playwright登录Spug，首次History356、第二次History357各一个最终POST，均实际写入前失败并保全。两处根因修复后第三次真实UI最终POST1/HTTP202，smallapp-a732505e94bc4863b568e2b2a8c17d57 / History358，真实UI RUNNING无错、观察POST0。原worker28413实际FD65536继承，完整归档校验中，不重派旧号或自动再试。
3. [x] History356 FD预算不足及History357缺演练iptables两根因均修复，均mutationDispatched=false且885表/UUID/全部业务保持。持久FD65536、写入前失败显式准许aab0b3f7（206行为+15封包）、MAIN实际执行依赖288d4c39（86项回归）通过；两次专属clean副本构建安装122SHA校验PASS，原56失败pins保持。每次正式v2准许后才真实新UI提交，本地原回执在restore-attempt-1/2，新旧关联不改。
4. [x] History358原失败保全后，动态附加网络生命周期修复76bb60bd及f819fbed实际RED/GREEN/157回归通过；精确构建安装和真实停写observe通过。正式v1写入后准许后，UTC16:13真实Spug一次最终POST/HTTP202启动History359 / smallapp-a63174ccdf0c42f187f182e172653759，UTC18:34:41.896554原生SUCCEEDED/实际exit0。885表/512156行完整结构与数据、5916附件版本/4920唯一内容、引用及Redis独立校验通过，原五服务运行/后端UP/前端200。恢复后实际Chrome登录用户管理2117条/20行、版本2026-11-03-12-15-42、业务写入0通过。
5. [x] 最终原包、暂存清理、预约释放、203远端失败pins与28本地原失败文件保持、196其它业务及正式源原运行态通过。四个专属发布worktree实体及Git注册均删除、自有测试容器/卷无残留、控制组件在稳定路径运行，closeout-verification.json PASS。四次实现已分别提交；最终记录UTF-8/语法/私密值核验、原字节保全规则及实际暂存diff检查全部通过，按限定范围单独提交最终记录。首次记录检查失败及其修正留在execution-log，不改变原始证据或服务器。

## 最终结论
正式新FULL经真实Spug恢复到备份/审查服.59已完成。History359原生SUCCEEDED/exit0及全部独立数据、运行态、真实页面与保护检查通过，收尾验证PASS；详见verification-report.md。原三次失败和准许链完整保留，不宣称首次操作即成功，也不宣称正式服.57目的地已验收。

## 预期验证
Given 正式来源新 FULL 完整且 .59 原 MAIN 当前准入通过、无活动冲突；When 在真实 Spug 页面选择该包和 .59 并一次最终确认；Then 同一操作真实成功退出，恢复数据和附件/引用/受控Redis独立校验通过，原目标服务及真实业务页面可用，无关业务保持，失败历史保留。

## 经验门禁
- Trigger：Spug 主实例跨服覆盖恢复、PROD 级 .59、真实页面长链路及操作接续。
- Preflight check：读取经验索引命中的恢复合同及现行服务器/登录/备份恢复规则、PowerShell UTF-8；核实际 Spug 入口、当前原容器/镜像/UUID/网络/数据归属、全部 writer fence、共同锁及原操作、NAS canonical 只读归档和精确 FULL pins。真实 E2E/恢复前记录 experience-preflight PASS。
- Blocker：未知活动任务、资源/配置/pin/版本漂移、writer 归属不明、来源/目标准入失败、无真实 UI 入口或凭据，停止对应动作；失败不能变成功，超时不能推断终态。
- Verification：真实一次 UI POST 及 operationId、原进程 exit 与结果 pins、数据库全结构/行、对象内容/版本、引用及Redis、原容器/镜像/UUID、health/HTTP和登录后真实页面分别留证。
- Forbidden action：不用 API/SQL 代替页面提交，不以选择取消或测试服成功替代 .59 恢复，不删除失败 claim/预约/原材料、不静默降级/盲目重试，不碰 NAS 数据/其它业务或受保护本机资源。
- Evidence：本目录 execution-log.md 与脱敏回执；原始敏感配置和数据仅 C:/Spug/runtime/private/ 下本任务目录。固定 E: 文档若不可用，仅使用已确认 C:/SpugHandoff/release/repository/docs/ 权威副本并记录。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，使用已验证的正式恢复引擎与真实 UI 合同，必要修复先复现再实现。
- 是否存在临时补丁或绕过：否。
