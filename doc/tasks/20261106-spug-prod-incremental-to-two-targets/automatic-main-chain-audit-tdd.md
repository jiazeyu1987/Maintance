# MAIN cycle 原生链验真接入

## 目标与当前状态

沿用 continuation-review-20261110-r6.md。仅重构本机验收工具，使已受理的 v3 UI 增量提交显式绑定当前 v4 安装选择及真实 147 文件标准包；保留原 130 文件与 stage 合同，不重复 FULL 或提交备份。状态：in_progress。

里程碑：BDD/RED → 最小 MAIN 分支 → GREEN → 旧链/混合代次回归 → 父代理独立实际验真。预期本机验证不接触远端，不宣称本轮业务备份已成功。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。v3 必须显式 --selection，且必须 v4；未知 spec 不接受 147。
- 是否从根因和长期维护角度解决：是。显式区分安装合同代次，复用正式 v4 完整验证器，不修改旧 package_manifest 的 130 合同。
- 是否存在临时补丁或绕过：否。结果沿原 AutomaticBackupChainAudit/v1 以兼容原 375 父链，但新增 MAIN cycle/部署绑定；原件不修改。

## 经验门禁

- Trigger：自动增量异步原件/当前安装代次接入。
- Preflight check：核原 operationId、提交计划和父链；从正式 v4 选择验证完整闭包，实际标准包逐文件核 SHA，安装侧原件仍逐项验证。
- Blocker：缺 selection、v3/v4 绑定错配、未知合同、包/安装文件/原输入漂移、父链错配、未有成功 owner 终态均拒绝。
- Verification：真实临时文件/归档的正反例、实际 v4 只读本机 prepare、旧 130/stage/链验证回归；最终远端验真由父代理独立执行。
- Forbidden action：不重发已预约 I1，不重做 FULL，不把 RUNNING/launcher exit2 当成功，不改旧 point/audit/receipt，不为新合同扩大旧 130 门禁。
- Evidence：docs/release-agent-checklist.md“自动增量链与恢复周期门禁”“实际封包构造配置传递门禁”，本日志及本阶段实际测试日志。

## 接口与 BDD

prepare(..., *, selection_path=None, task=..., private=...)；CLI --selection。仅 AutomaticIncrementalUiSubmission/v3 生成 MainProgramAutomaticBackupChainAuditSpec/v1。v4 读者与正式 select 使用同一个 validate_publication_v4，避免重复读取完整闭包。MAIN 固定当前标准包 147 项的显式版本合同；旧入口保持 130。

- Given 真实 v3 submission、当前 v4 完整原件、原 375 PASS 父链；When 仅本机 prepare；Then 生成绑定 cycle/selection/control/spug/capture/owner/原 baseline 的 147 spec，零远端调用。
- Given v3 缺显式选择、选择字节变化或 v4 字段/提交身份错配；When prepare；Then fail fast，不加载旧 stage 作为替代。
- Given 真实临时 147 文件标准包及安装树；When 新显式 spec 验证；Then 每个归档与安装文件 SHA、manifest 及完整 SAFE reader 合同通过。
- Given 同一 147 包且旧/未知 spec、缺文件、额外/链接/穿越成员、载荷或摘要变化；When 验证；Then 拒绝。
- Given 原 130/stage 与链验真测试；When 回归；Then 原合同保持。

## TDD 证据

待记录实际 RED/GREEN/REGRESSION。测试中的临时归档与安装树仅验证只读协议；唯一实际部署输入用原 v4 reader 读取，不伪造实际业务成功。

- 首轮 23 FAIL/exit1，14 项卡在载体误写 common/smb_readback.py；这是载体错误，不计为产品 RED。已按现有 verify_package 的真实 common/repository_native_readback.py 精确修正，生产未改。
- RED：`python -X utf8 -B -m pytest TASK/test_automatic_main_chain_audit.py -q -p no:cacheprovider --tb=short`，原会话 73568 实际 exit1，16 FAIL/7 PASS/0 skip，34.58 秒。失败均为缺新 package/config API 或 prepare.selection_path；旧 147 拒绝合同与已有检查通过。
- GREEN：同一新文件 23 PASS/0 skip，原会话 37827 实际 exit0，37.00 秒。包含实际 v4 全闭包纯 prepare。
- REGRESSION：test_automatic_chain_audit.py、test_mixed_generation_evidence.py、test_automatic_dispatch_audit.py、test_automatic_stage_deployment.py，原会话 29224 实际 exit0，78 PASS/0 skip，40.90 秒。未接触远端。
- 最终自审 BDD：Given 当前原 capture 本身未变，但本次 request-inputs 指向另一个 capture；When MAIN 专用配置验证；Then 必须拒绝，不能仅证明另一个配置可经 binder 重建。新增 1 项真实私有文件反例，先单独 RED。
- 精确新增 RED：`pytest TASK/test_automatic_main_chain_audit.py::test_main_actual_request_capture_must_equal_submitted_original_pin -q -p no:cacheprovider --tb=short`，实际 exit1/1 FAIL/0.42 秒，DID NOT RAISE，原 capture 自身与摘要均仍正确。
- 最小修复仅在 MAIN 配置验证中增加本次 request-inputs 的原 owner/capture pin 全等核验；原载体补正式 taskRoot、operationId 和真实私有 request-inputs（不改其原 pin 漂移期望）。MAIN prepare 同时把最初 submission/parent/baseline 原字节 pin 放入结束复核集合，读取同一 raw 后再解析，防止末尾重新取样掩盖漂移。
- 最终 GREEN：新完整文件 24 PASS/0 skip，原会话 2594 实际 exit0，22.33 秒；先前 78 回归证据保留。最后修改仅触及 MAIN 专用分支，没有再次广泛重跑已通过旧分支。
- 静态验证：三个 Python 文件显式 UTF-8 读取并 compile PASS；两个已跟踪源码 git diff --check PASS。未启动服务器、Docker、浏览器、备份或恢复；未改提交、安装、父审计或任何业务原件。

## 冻结交付

代码/测试已冻结，当前整体 r6 任务仍 in_progress，父代理独立核验真实 operation 终态及必要提交。此阶段不宣称 I1 成功或来源独立健康已通过。

精确交付为 verify_automatic_backup_chain.py、automatic_chain_audit.py、test_automatic_main_chain_audit.py 和本日志。父代理命令：

```text
python -X utf8 -B TASK/verify_automatic_backup_chain.py --submission automatic-main-20261110-r6-i1-ui-submission.json --parent automatic-i2-audit.json --selection main-program-current-installations-45dd7dc-r6-v4.json --output <独占新audit文件> --prepare-only
```

移除 --prepare-only 才会派发原只读审计，必须先由父代理确认原操作唯一成功终态、经验门禁及来源现态。默认 120 秒元数据/150 秒远端运输预算保持。输出仍 AutomaticBackupChainAudit/v1，含原 MAIN cycle 与部署/配置/baseline pins，可作为下一次增量的父审计；旧 375 审计没有修改。
