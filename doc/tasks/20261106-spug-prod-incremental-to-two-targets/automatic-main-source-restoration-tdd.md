# MAIN cycle 来源恢复验真 TDD

## 目标、里程碑与当前状态

沿用 main-source-restoration-refactor-plan.md；状态 in_progress。仅本机验收工具接入：BDD/RED → MAIN 显式合同 → GREEN → 旧合同回归 → 父代理实际验真。当前现场 audit/UI terminal 尚未产生，不创建现场成功原件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。cycle/selection 成对、MAIN v3/v4 明确绑定，不伪造旧 stage；显式 audit/parent 限定 TASK 内。
- 是否从根因和长期维护角度解决：是。复用已提交 prepare_package 的完整 v4/147 合同一次，消费其已核本机 pin 集合中的明确 generation/plan/private plan 原件提取 policy，不重复扫描完整闭包。
- 是否存在临时补丁或绕过：否。旧 validate_evidence 与 130 合同保留。现场 SCRIPT 的 SQL、服务、健康、Redis、锁、epoch、无 worker、原件门禁保留。

## 经验门禁

- Trigger：自动增量新 cycle 成功后的独立来源恢复验真。
- Preflight check：同一 v3 submission、147 MAIN audit、真实 UI v3 成功终态、verify observation/baseline 与当前 v4 完整部署、原 owner/capture/UUID/epoch 全绑定。
- Blocker：缺终态、混合代次/cycle、错误父链或配置、未知 worker/锁、SQL/服务/原件漂移即停止。
- Verification：真实本机文件与实际 v4 只读 reader；临时结构用例明确只是证据协议，不称真实业务成功；旧合同回归。
- Forbidden action：不重发业务、不创建现场 audit/terminal、不跳过旧检查、不将 I1 的未重验原件声称全 SHA 通过；FULL/I2 仍须完整 10044 原件。
- Evidence：docs/release-agent-checklist.md 自动增量链门禁、父计划与本日志。

## 接口及 BDD

prepare(kind, *, cycle=None, selection_path=None, audit_path=None, parent_path=None, task=TASK, private=PRIVATE)。MAIN 输出明确 MainProgramAutomaticSourceRestorationSpec/v1，安装对象明确 MainProgramAutomaticSourceInstallation/v1；旧调用不变。

- Given 当前真实 v4/147 闭包和同 operation 的协议 submission/audit/terminal；When 本机 prepare；Then 一次正式 prepare_package，原 policy 与两控制器绑定，I1 failedPins=[]。
- Given FULL/I2；When MAIN 合同验证；Then failedOriginalFullShaRequired=True，原现场 10044 原件核验代码保持。
- Given 任一 audit/UI/部署/配置/链/时间错配；When 读取；Then 远端前拒绝。
- Given verify baseline；When 核 UI terminal；Then 它绑定原提交计划及原 operation，允许其 pin 不同于提交前 baseline，但部署五 pins 必须相同。
- Given 同 TASK 已有输出、缺一半参数、越界 audit/parent 或旧 v3/stage 混用；When prepare；Then 不覆盖且拒绝。
- Given 旧 130/stage 合同；When 原测试回归；Then 原检查保持。

## 验证记录

以下为实际 RED/GREEN 记录。测试正例采用临时协议文件，不保存为 TASK 现场成功；实际部署只由正式原件读者验证，不调用服务器/Docker/E2E。

- RED：新文件 33 项，原会话 38749 实际 exit1，32 FAIL/1 PASS/0 skip，15.04 秒；失败为缺 MAIN API/prepare.cycle。正式 package reader 已实际完成本机 v4 闭包读取，原 SCRIPT 保留断言通过。
- 第一候选实际 11 FAIL/22 PASS/0 skip，原会话 72390 exit1/29.07 秒。根因为把 SourceBackupEpochSnapshot/v1 误当 event 的 UUID/identity 结构；正式 snapshot 只有 policySha256/epochId/state/eventPin。最小改为核原完整 policy 的 canonical SHA 与 snapshot.policySha256，再核 audit.database.endPosition.databaseUuid，未放宽 epoch 合同。测试原断言同步改为正式 policy digest；临时文件根载体明确补原 automatic_chain_audit.py 供原共享 probe 读取，不替换生产 probe。
- GREEN：`python -X utf8 -B -m pytest TASK/test_automatic_main_source_restoration.py -q -p no:cacheprovider --tb=short`，原会话 54309 实际 exit0，33 PASS/0 skip，28.83 秒。包括原 v4 完整闭包与完整 MAIN prepare 文件根协议接线；临时audit/terminal不代表本轮业务成功。
- REGRESSION：`python -X utf8 -B -m pytest TASK/test_automatic_source_restoration.py TASK/test_mixed_generation_evidence.py TASK/test_automatic_mixed_generation.py -q -p no:cacheprovider --tb=short`，实际 exit0，47 PASS/0 skip，3.00 秒。旧测试未改。
- 静态：两个本轮 Python 文件显式 UTF-8 读取/compile PASS；源码 diff --check PASS；旧 test_automatic_source_restoration.py 与已提交 verify_automatic_backup_chain.py 无修改。
- 父任务独立验证：原会话 82558 实际 exit0，33 PASS/0 skip，27.97 秒；运行前核两个实现/测试文件字节数与 SHA256 均等于子代理冻结值。仅验证证据读取合同，不代表现场新备份已成功。

## 冻结与父任务接入

本阶段代码/测试已冻结；整体任务仍 in_progress，尚无本轮现场成功声明。仅交付 verify_automatic_source_restoration.py、test_automatic_main_source_restoration.py、本日志；未访问服务器/Docker/浏览器，不提交、不清理、不重发操作，不生成现场成功原件。

父代理在真实 UI verify 与原生 audit 均已成功后使用：

```text
python -X utf8 -B TASK/verify_automatic_source_restoration.py --kind I1 --cycle main-20261110-r6 --selection main-program-current-installations-45dd7dc-r6-v4.json --audit <本轮独占audit文件名> --parent automatic-i2-audit.json --prepare-only
```

移除 --prepare-only 才派发既有只读现场检查。增量 MAIN 必须提供显式 TASK 内 parent；audit 默认 cycle 命名或可显式指定 TASK 内原件。输出固定 cycle 命名且已存在即拒绝。终态 verify baseline 可不同于提交前 baseline，但须绑定原计划和原操作；对应真实 UI observation 必须 SUCCEEDED_VERIFIED，零业务 POST、零阻断、零页面错误。源 policy 从原已核闭包明确路径原件提取，不再次加载 v4 安装；最终现场读取后仍逐项复核完整本机 inputPins。
