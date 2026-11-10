# 自动增量链策略准入 TDD

## Current Status

completed（仅本子任务的本机实现与验证范围）；8 个实现/测试文件已冻结交父任务独立复核。真实 376 的 FAILED_RETAINED、原策略、原件与半成品未修改。本轮没有服务器、Docker、浏览器、安装、提交或清理；根任务的正式提交、封包安装与真实页面验收尚由父任务继续处理。

## 目标、里程碑与预期验证

按 automatic-chain-policy-admission-fix-plan.md，将既有 owner 的 maxChainAgeSeconds/maxChainPoints 同时纳入计划与采集前准入。超过期限或已有点数满时 BASELINE_REQUIRED，非法策略/根时间 BLOCKED；保留末端检查。里程碑为 BDD -> 真实 RED -> 最小实现 -> 新合同与受影响回归 -> 原字节/SHA 冻结交父任务。

批准范围：ops/recovery/repository_records.py、backend/src/main/resources/recovery_control_incremental_plan.py、ops/recovery/repository_minimal.py、ops/backup_engine/standard_fixes.py、ops/spug/smallapp-ui/app.js；新增 scripts/tests/test_incremental_chain_policy_admission.py；原 planner fixture 补明确策略与 createdAt，backup_variants 仅最小 allowlist；本独立日志与原始测试输出。无新包成员/schema、无策略放宽、无远端/Docker/浏览器/安装/提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；已到期明确要求经原确认路径建立 FULL，未知输入必须失败。
- 是否从根因和长期维护角度解决：是；共享纯策略语义，计划及两模式实际采集入口共同使用，保持原完整链/epoch/末端检查。
- 是否存在临时补丁或绕过：否；不修改失败点、策略、原时间或原操作，不静默转 FULL。

## 经验门禁

- Trigger：自动增量计划 READY 与原生 REPOSITORY_NEW_FULL_REQUIRED 矛盾；正式包为冻结基线加 transforms。
- Preflight check：已只读核当前 owner 合同、标准 baseline 的 MinimumConfiguration/publish、实际 build_variants 交付与原 Native.resolve 重算；先用真实 tmp 元数据与实际封包入口复现。
- Blocker：非法策略/根未来时间/不可解析、当前链不完整或有分叉、原 pin/epoch 漂移、不能在首采集前阻断，均不得交付成功。
- Verification：RED/GREEN/REGRESSION 记录命令/退出码/零 skip；两实际封包新进程以真实临时原件运行到首次采集边界；旧计划/现 FULL 确认合同回归。仅本机测试，不代替安装或页面验收。
- Forbidden action：不增超时/策略、不加隐式默认、不隐藏异常、不仅改轻量源码、不手填 runtime 对象替代实际封包构造、不远程执行或重派 376。
- Evidence：父计划、main-program-chain-age-failure-r6.json、本日志与对应 raw logs；经验入口 docs/experience-index.md 的自动增量链/实际封包构造门禁。

## BDD（实现前）

1. Given 同源完整成功链，When 根当前年龄 >= owner 最大年龄，Then BASELINE_REQUIRED 并有明确到期原因；等于期限即到期，未过期保持 READY。
2. Given 完整唯一链，When 已有点数 >= maxChainPoints，Then BASELINE_REQUIRED；已有 maxPoints-1 时允许下一点恰好达到限制。
3. Given 缺失/布尔/字符串/零/负数策略或无效/未来根 createdAt，When 预览，Then BLOCKED，不伪称缺少全量。
4. Given READY 计划后排队或 SMB 预检耗时跨过期限，When 实际 standard/lightweight 首次采集前，Then 明确拒绝，首采集/停写未启动；原末端完整性/时限检查保持。
5. Given 合法策略，When 重复预览或当前时钟正常前进且仍未到期，Then parent/root 与稳定摘要不变；策略或根 manifest pin 改变必须影响原摘要。
6. Given 两个真实生成包，When 新进程运行原配置构造及 publish，Then 同一准入逻辑实际接线可达，旧 FULL 流程不受增量时限限制。

## 执行记录

已识别现有任务，读取父计划、经验索引及命中的自动增量链与实际封包配置传递门禁。父任务审阅通过最小设计后进入 RED；尚未执行服务器/浏览器/安装。

RED r1: 指定 Python `-X utf8 -m pytest -q scripts/tests/test_incremental_chain_policy_admission.py --tb=short` -> exit1，38 FAILED / 8 PASSED（70.94秒）；原始日志 automatic-chain-policy-admission-red-r1.log。已实际复现 planner 对已到期/点数满仍 READY，以及标准封包已过期和 SMB 预检跨期限仍到达首次 capture 边界。另有 8 项因测试误将 lightweight 文件数也写为147而失败，属于载体错误，不计为产品缺陷；实际 lightweight 为146。原始失败完整保留，修正测试前提后重跑。

RED r2: 同命令（新增观察期间/配置读取期间跨期限场景，文件数按实际 standard147/lightweight146）-> exit1，37 FAILED / 12 PASSED（101.18秒）；原始日志 automatic-chain-policy-admission-red-r2.log。失败集中于缺失共享准入 API、非法策略仍伪称缺基线、过期/满链仍 READY、缺根 manifest 明确 evidence，以及两个实际封包的采集前拒绝缺口。至此才开始最小产品实现。

测试环境：PYTHONPATH=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies，PYTEST_DISABLE_PLUGIN_AUTOLOAD=1；Python=C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe。使用真实临时文件与新进程实际封包构造/catalog/publish；本机 LocalReadback 仅替换远程传输，实际比较探针文件 pin/字节，首 run_child 明确抛边界异常，绝不声称真实 SMB/数据库/备份成功。

既有合法范围来源：冻结标准 MinimumConfiguration 的 maxChainPoints 为严格 int 且1..1024，maxChainAgeSeconds 为严格正 int（无新增年龄上限）。共享检查沿用该现有 owner 合同，不新设产品限制。旧 MetadataFixture 的长期历史时间采用显式大年龄协议策略，边界用例使用原86400/16或明确更小限制；不修改任何运行策略。

## 最小实现与后续 TDD

共享 incremental_chain_policy / incremental_chain_admission 位于既有 repository_records.py；不新增文件成员或 schema。planner 先验证实际 owner 策略，在当前完整唯一链及 epoch 核验后、任何 live source observation 前检查根 manifest.createdAt 与已有链点数。到期返回 INCREMENTAL_CHAIN_AGE_EXPIRED，满链返回 INCREMENTAL_CHAIN_POINT_LIMIT_REACHED，两者均 BASELINE_REQUIRED 并沿用明确 FULL 确认路径。非法策略/根时间或未来根为 BLOCKED。evidence 保留原 ownerPin 并显式加入根 manifestPin，now 不入摘要。

标准封包只从认证冻结 repository_records 原件（SHA256 f192fe6222b295c59844ed375776dc2f7bdafce3bf1b625c5b08053f64c032af）精确移植两函数；上下文或基线漂移立即失败。标准/轻量的实际 publish 都在读取父链后检查，并在首次 capture run_child 前再次检查；标准第二处位于 SMB 预检之后。未改 dispatcher，原 Native.resolve 的计划重算保持；未改 simple.js。app.js 只加两项中文原因。

GREEN r1: 新文件原49项 -> exit0，49 PASSED（96.72秒），日志 automatic-chain-policy-admission-green-r1.log。

审查新增同一缺口边界：最后 reader.finish 的原件身份复核本身也可能跨期限；同时补父任务要求的已失效不调用 live observation、真实策略/根 manifest 原件变化影响摘要及标准末端原 require 的完整 AST 保持检查。聚焦 RED: `PYTHON -X utf8 -m pytest -q scripts/tests/test_incremental_chain_policy_admission.py -k "final_freshness or expired_or_full_chain_never or policy_and_root_manifest" --tb=short` -> exit1，1 FAILED / 3 PASSED / 50 DESELECTED（12.98秒），日志 automatic-chain-policy-admission-red-final-freshness-r3.log；实际最后复核跨期仍 READY。最小修正仅将 reader.finish 放在最后年龄复核之前，最终响应形成前才允许 READY；其余原件/epoch/链检查保持。

## 最终 GREEN / REGRESSION

最终 Python 命令均使用前述同一指定 Python 与 PYTHONPATH；环境 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1、PYTHONDONTWRITEBYTECODE=1，公共前缀为 `PYTHON -B -X utf8 -m pytest -q --tb=short`。每组在独立本机进程运行，所有会话均已终止。

| 组 | 参数 / 命令 | 实际终态 |
| --- | --- | --- |
| 新准入合同 | scripts/tests/test_incremental_chain_policy_admission.py | exit0，54 PASSED，147.07秒，0 skip |
| 原计划完整回归 | scripts/tests/test_automatic_incremental_plan.py | exit0，40 PASSED，205.43秒，0 skip |
| 受影响实际封包回归 | scripts/tests/test_backup_variants.py::test_standard_keeps_original_code_except_reviewed_fixes_and_archive_names；::test_changed_safe_baseline_patch_context_is_rejected；::test_automatic_incremental_components_execute_from_real_package；::test_variant_package_entries_and_real_file_manifest | exit0，6 PASSED，17.14秒，0 skip |
| Spug 自动入口 / HTTP / proxy | ops/spug/test_automatic_incremental_entry.py；ops/spug/test_automatic_incremental_http.py；ops/spug/test_automatic_incremental_proxy.py | exit0，21 PASSED，4.53秒，0 skip |
| 原 UI 安全与 FULL 明确确认合同 | NODE --test ops/spug/smallapp_ui_safety.test.cjs | exit0，70 PASSED，213.1527毫秒，0 skip |

NODE=C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe。最终共191项通过、0失败、0跳过。封包回归选择直接受影响的原标准完整字节合同、精确上下文失败、两模式自动组件与实际入口/manifest；没有执行无关的 Linux O_PATH 归档租约测试，也未以其 Windows skip 充当通过。父任务已知本轮不运行 Docker 或远端。

新54项包含 standard147/lightweight146 实际封包新进程的合法、过期、满链、下一点恰好满、未来根、非法策略、配置读取跨期限、标准 SMB 预检跨期限以及 FULL 路径；全部运行原 MinimumConfiguration + MinimumCatalog + publish，到首次采集拒绝/可达边界。到期/满链已证明 live source observation 没有调用。真实 tmp owner 与根 manifest 变更及对应传递 pins 证明 planDigest/evidenceDigest 变化；时钟在未到期范围内正常前进则摘要不变。标准封包最终原年龄 require AST 与认证 baseline 完全相同。

末端合同明确保持：如果采集执行期间才跨过最大年龄，仍由原末端 REPOSITORY_NEW_FULL_REQUIRED 拒绝；本轮不预测运行时间、不放宽期限、不发布原失败半成品、不把后续失败伪称成功。

## 字节与编码冻结

全部8个实现/测试文件显式 UTF-8 解码/回编码相等、无 BOM；所有 Python 文件内存 compile 通过；git diff --check exit0。Git 对3个已有文件提示将来 checkout 的 LF/CRLF 设置，当前文件未做额外换行转换；以下均是当前工作区实际原始字节 SHA256。最终日志更新后再单独验证自身 UTF-8/无 BOM 与指纹。

| 文件 | bytes | SHA256 |
| --- | --- | --- |
| ops/recovery/repository_records.py | 20765 | 10807ebdd3b82d27e882adfe5bf8926744c049126eb2380069a86f14421f833a |
| backend/src/main/resources/recovery_control_incremental_plan.py | 21845 | 47bbc3a0d1749fd70900b6dc93f2d519f97c6c0b8e2bbe4c9bbe10b800e6e0fb |
| ops/recovery/repository_minimal.py | 42077 | f553c94a027e367f04109c754018cbf125e029b4ed45b814f5096279b10fd26b |
| ops/backup_engine/standard_fixes.py | 48706 | 922529c33f007c7cdec9b658ec16052337c98bd96029b42ed62facb520ef603e |
| ops/spug/smallapp-ui/app.js | 32269 | d74c9f512a416c8925a47ca625297bbeb1c5984a7697d6e2002235cbc78371ea |
| scripts/tests/test_automatic_incremental_plan.py | 38068 | 27b5351635261ef060c1cb791dbbea43c08a3096f1d616c876dc9774bf495606 |
| scripts/tests/test_backup_variants.py | 30474 | d360fbf18ce96b2a878605e4d07260c51d52d656b76e4a48d1d0953647fb1af4 |
| scripts/tests/test_incremental_chain_policy_admission.py | 20943 | 32ff4081c01716b185c17b5c64f4a5d4b94b8ff9b58f1e8efbc9c735534c7d18 |

## 原始日志 pins

所有日志位于本 TASK，原 RED 未覆盖或删减。r1载体成员数错误已如实区分；r2 与 freshness r3 是产品缺陷真实 RED。

| 文件 | bytes | SHA256 |
| --- | --- | --- |
| automatic-chain-policy-admission-red-r1.log | 26010 | a339aaa5f8fc839dfeb679075b640f9c8948d31d1af087ca72bfe614d707a5ae |
| automatic-chain-policy-admission-red-r2.log | 23950 | dbd242dc4b591333386a86b8ff0f3e1c06a608f31013101a5f6185563fa54952 |
| automatic-chain-policy-admission-red-final-freshness-r3.log | 907 | 4b67ea0cfd1a1f6364da90d4b6bbc5fcfb0109a187508c4e170c00b0d6bc2667 |
| automatic-chain-policy-admission-green-r1.log | 112 | 4ccf7a3f009cc19840e145331fdf7873dddb53d1734d9937c3071beee421df5a |
| automatic-chain-policy-admission-green-r2.log | 113 | 74e0eb5f2cd482eb09be445ca96889480678b27f4d8a1639b1a7c36590ae0869 |
| automatic-chain-policy-admission-regression-planner-r1.log | 113 | 4aea33a84e54a314e551fec1adc1d453268bde1b11d5c1c3e22cc543acf5c481 |
| automatic-chain-policy-admission-regression-variants-r1.log | 101 | e4e81abc8a66651335392f838992a738c46d46140117bffd9fdb1dfd9824d1d9 |
| automatic-chain-policy-admission-regression-spug-r1.log | 101 | 5a18aa0acc43f9c9d734e5b286dee03aad5abb5702652e4e87068dcff9f245bf |
| automatic-chain-policy-admission-regression-ui-r1.log | 7140 | 33bfbfebd7da7d27e3f6646e65b24656501a8979a8a0a1a4721f2fa07fc22886 |

## 交付边界

本机合同通过不代表远端已安装、来源实际健康、真实按钮或新FULL/增量/恢复已成功。父任务独立复核后再提交及通过正式干净发布 worktree 执行实际封包安装流程；原376和全部已失败材料保留原样。本子任务没有创建需清理的 worktree、运行控制台或远端操作。

## 父任务独立复核

2026-11-10：父以记录在 `automatic-chain-policy-admission-parent-r1.json` 的原命令独立重跑新54项，exit0，54 passed / 0 failed / 0 errors / 0 skipped，运行107.437秒；八个实现/测试文件 SHA 与运行前完全一致。独立 raw 输出250 B / SHA256 `3c72d57fb960ede81770affa75b45ace31a92ff53b08f086ed94667bcd4cf259`；JUnit 9658 B / SHA256 `2632379f21b782a5fb69474361f0cd6b05cf68c1d716ceb5fb9a3b8594d79e0b`。父另独立复跑旧计划40项、受影响封包6项、Spug入口/HTTP/proxy 21项以及原UI安全合同70项，均 exit0、0 skip，总计191项通过。初次父命令遗漏 private test-dependencies，三个 Python 收集命令因无 pytest 失败；按本日志既有 `PYTHONPATH` 修正环境重跑通过，未记为产品 RED。未接触服务器/Docker/浏览器/安装/提交；现网仍未包含该修复。

提交证据说明：仓库默认忽略 `.log`，本次仅将上表九份脱敏检查通过的原始测试日志显式加入。RED 原件带 pytest 生成的 `E` 行末空白，完整 staged `diff --check` 因这些原始行返回2；不修剪、不转换证据原件。实现、测试、计划与结构化复核报告单独执行 `diff --check` 通过。原件 SHA 与表格逐份相等。
