# Stage 2 B ordinary owner 共用派生接缝 TDD

## Current Status

ready_for_closeout（仅本子任务本机实现与有限Windows验证范围）；继续同一根任务。本接缝已完成并冻结，父独立Linux完整入口/权限/三原件验证、正式依赖闭包集成与提交尚未完成。没有远端、Docker、HTTP服务启动、安装、提交或清理；不宣称真实恢复或完整for_request验收完成。

## 目标、里程碑与预期验证

父任务已审 A1 纯模块 recovery_restore_inputs.py。只读核对现 ordinary 派生与 A1 的完整语义，先形成 Given/When/Then 与真实 RED，再将普通请求 owner 的确定派生调用 A1 共用函数。实时 HTTP/source_admits/quarantine、持久化、三原件与历史仍保留原控制器职责。若 A1 无法严格承载现语义，具体报告接缝缺口而不扩展。

里程碑：只读设计 -> BDD/RED -> 最小实现 -> ordinary 专属与原合同回归 -> 字节冻结交父复核。预期验证包括原请求语义、失败与证据 pin、直接调用真实 A1、现源身份/三原件约束/历史不退化；只跑有限 Windows 合同。

允许修改：backend/src/main/resources/recovery_control_restore_catalogue.py；独立新增 ordinary 专属测试；本独立 TDD 日志及原始测试日志。禁止修改 A1/e633/A2 consumer、native/http/files/UI 及其他代理文件。Docker/SSH/HTTP 服务启动/浏览器/安装/提交均 HOLD，Linux 验证由父独占。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；保留原失败路径与完整证据，不以 mock 成功代替真实派生。
- 是否从根因和长期维护角度解决：是；唯一 owner 确定算法归 A1，controller 只组织现运行职责。
- 是否存在临时补丁或绕过：否；不复制第二套派生算法，不扩大到 choice/page/保全恢复接线。

## 经验门禁

- Trigger：ordinary 控制器确定 owner 派生与已审 A1 重复；本任务为严格有界重构。
- Preflight check：先读适用 AGENTS、前任务终态、经验索引、PowerShell 编码规则，继而核对命中的恢复输入与真实测试经验；产品修改前确认 A1 原字节 SHA 与原 owner 完整语义。
- Blocker：共享 API 不能保持原 owner 语义、证据 pin 或安全失败；依赖/测试数据缺失；测试失败均如实记录，不继续声称完成。
- Verification：独立临时原件调用真实函数，先 RED 后最小实现与原合同回归；记录命令、退出码、真实终态及 SHA。
- Forbidden action：不远程、不 Docker、不服务启动、不安装/提交、不改原件、不修改其他代理拥有文件、不以跳过或模拟成功掩盖失败。
- Evidence：本日志、父消息、原实现/A1 SHA、专属 RED/GREEN raw logs。共享 request-command-log.md/execution-log.md 由父统一收录，避免并发覆盖。

## 执行记录

UTF-8 只读 bootstrap 已核适用 AGENTS、前子任务终态与经验索引。PowerShell 对 E: 路径的 Get-Content -Encoding 参数未能解析，尚未运行风险命令；接下来用指定 Python 显式 UTF-8 读取并核路径，不以该读取失败冒充通过。

## 只读设计与 BDD（产品修改前）

父接受本有限设计：for_request 保留 source_admits、_bind_archive_chain 唯一发现及完整 point binding、全部父点实时资格；最终 owner 改为真正调用 A1 derive_archive_restore_owner。不传 reader；A1 自己读取真实 pin/metadata。guard 只核本请求已读 metadata 物理身份、已观察目录/quarantine，不重复全载荷扫描或每次完整 hash；derive 后保留最终完整 SHA freshness barrier。旧 bind_archive_chain/archive_references 的算法与外部行为不改。本阶段不接 choice/page/新保全恢复。

已核 A1 15977B/SHA256 a1d42136c4cb39f57e119da42416fd97157db0ad7a664bdb8ca4bb0bd65c1ad0；改前 controller 20770B/SHA256 d6dfd4701a5a6343af71329167b1167952b3328b4a52568e9ff21ae060c84ab9。A1完整派生保留base owner所有未选source/targets/policies/limits/operationsRoot字段，所选scope与链pins不平移。v1 primary identity原pin也严格读取；总metadata64MiB仍按A1已审合同。

父指出共同文档的本机可读路径为 C:/Users/D01021/Documents/ChatGPT/IntRuoyi/docs；已显式UTF-8读取 powershell-memory.md、release-backup-restore.md。本轮不需要服务器连接文档。命中维护仓经验：Python JUnit/WMI必须核进程实际退出/有效XML；测试载体必须明确区分失败边界与成功，不能把缺前提当产品RED。所有风险动作仍HOLD。

BDD:

1. Given 真实普通 FULL 或 FULL+2INC、三种明确 target、原完整base owner与实时来源协议响应，When for_request 派生，Then 恰好调用真实A1，入参是同一request/base与真实binding，输出逐对象等于原链派生owner；其余字段逐字节语义保持。
2. Given v2明确历史scope及其原identity路径，When请求所选历史链，Then共用派生保持原scope/pins而不改路径、不重签旧点。
3. Given实时来源拒绝/历史quarantine、任一父点缺资格、重复ID、失败原exit或原pin变化，When进入相同入口，Then在private目录/持久化前拒绝，不写三原件，不授来源或目标成功。
4. Given发现结束后、A1开始前或进行中原owner/metadata/目录发生真实替换或新增，When共用派生/末端屏障，Then拒绝，guard错误向上传播；禁止吞异常返回旧owner。
5. Given三份既有request-owned原件，When相同请求再次解析，Then不改内容/身份；改变request、binding或derived owner则明确 ORIGINAL_RESTORE_CONFIGURATION_CHANGED，不重写历史。此项完整成功/权限与持久化仅由父独占Linux实际执行。
6. Given Windows无Linux root custody，When合法请求完成真实A1派生到原directory入口，Then明确专属Boundary STOP，只证明有限接缝，不计for_request成功/持久化通过。原持久化尾部精确AST冻结只是辅证。

测试载体：实际tmp JSON/payload禁止读取文件；source_admits全函数使用真实credential/access pin及实际响应文件，只有urllib传输换为本地文件载体，不启HTTP服务。A1 spy仅透传真实函数/观测真实结果，不mock成功。Windows在真实Linux directory入口主动抛STOP，Linux专属节点assert POSIX且不skip，父需以无可写祖先的独占 --basetemp 运行完整入口。原尾部从 import recovery_control_smallapp_native.directory 到返回值全部AST SHA256（改前）为 9e708b21626c94b89ed4adae489144174c07f6b0953a151aa4e455f028ed71ce。

## 原始 RED

固定 Python=C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe；PYTHONPATH=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies；PYTEST_DISABLE_PLUGIN_AUTOLOAD=1、PYTHONDONTWRITEBYTECODE=1。先有界15秒运行独立 platform.node 探针，实际返回非空；未改stdlib/hostname或服务。

RED r1：`PYTHON -B -X utf8 -m pytest -q -p no:cacheprovider scripts/tests/test_restore_archive_request_owner.py -k "not linux" --tb=short --basetemp=PRIVATE/stage2b-ordinary-red-r1/tmp --junitxml=PRIVATE/stage2b-ordinary-red-r1/junit.xml`，真实pytest exit1，13 FAIL/4 PASS/10 deselected/0skip，8.32秒；原始stdout 13126B、stderr0B，保存在 stage2b-ordinary-owner-red-r1.log，SHA256 6abc8e8eeb33d8dbc68c7b1bebcecfcdedeb2fb39d2e9d9dc898e53e51aaafc7。外层exit0仅表示记录器已保存实际exit1，不计GREEN。

失败准确命中缺失接线：合法三目标/FULL及链/历史scope在到达custody STOP之前未调用A1；primary identity原件变更仍到达custody STOP；A1期间原件变更及guard/最后SHA屏障场景也因共享函数未调用而不能触发。3项真实来源/父资格拒绝与1项原尾部AST已通过。10个Linux完整入口节点被此Windows命令显式不选，不是skip；它们保留给父真实POSIX，不能用17项有限接缝代替成功/持久化验证。此记录写完才开始产品修改。

## 最小实现与首 GREEN

controller 只新增现 _ArchiveReads 的 stat guard 提取：finish 原逐文件完整SHA核对之后调用guard，guard保留原最终全部文件身份、目录及quarantine观察。for_request 在全父实时资格通过后先guard，调用真实 derive_archive_restore_owner(...,guard=reads.guard)，然后原finish完整SHA屏障，才进入一字未改的private directory/immutable持久化尾部。没有传reader、没有mock输出、没有吞异常/增加超时；bind/archive_references/旧发现算法不改。

GREEN r1：与 RED 同命令，仅独占目录改为 PRIVATE/stage2b-ordinary-green-r1；真实pytest exit0、17 PASS/10 deselected/0skip、9.98秒。raw stage2b-ordinary-owner-green-r1.log 242B/SHA256 0c13fa73ccda1b0adf8c55612674fe45f080c5c504b9cbf414b3963eb21febda，stderr0B，JUnit有效落盘，独立会话已终止。此17项仅有限接缝，不称实际for_request成功。

随后仅补回归观察，无产品再改：1项实际executor.pinned_read透传计数，证明guard未使controller已读metadata反复完整hash，仍初次与最终各1次；source_admits自身access原件仍只1次。另补2项父Linux完整节点，覆盖v2历史scope真实三原件闭合、原0755目录custody必须拒绝。新测试共30项：Windows命令明确选择18 portable、12 Linux不选。Linux完整验证命令为 `PYTHON -B -X utf8 -m pytest -q -p no:cacheprovider scripts/tests/test_restore_archive_request_owner.py --tb=short --basetemp=<父独占0700目录且祖先无group/world写> --junitxml=<父报告路径>`；不带排除参数，30项均须实际通过且0skip。节点自身assert POSIX，不允许在Windows计skip。

## 合并回归首轮未获终态与有界复核

首次合并命令增加原 A1 文件、原 test_restore_archive_catalogue.py 整文件与原 TASK/test_archive_catalogue_request_reads.py，保持 -k "not linux"，独占 PRIVATE/stage2b-ordinary-regression-r1。外层实际超时240秒，session20011最终exit1且明确TimeoutExpired；当时连basetemp和JUnit都未生成。不能判断任何测试PASS/FAIL，不归因产品或WMI。该首轮wrapper在TimeoutExpired分支未保存subprocess捕获输出，故没有声称存在raw日志；真实工具trace保留于session20011，本记录明确该证据局限。未运行服务操作/批量终止，也未增加超时。

随后两个独立15秒诊断：platform.node实际exit0、0.093秒、非空17B；pytest --version实际exit0、0.343秒、8.3.5。再用同4文件/同筛选的独立 --collect-only，加15秒faulthandler诊断且外层30秒边界，真实exit0、104/116 collected（12 Linux显式deselected）、3.87秒；无traceback、无skip。原raw stage2b-ordinary-owner-collection-probe-r1.log 14285B/SHA256 620571dacf8a1c8869eed8598d2d55f87231ee7bc1c9a4a3106ad9ee28427dcb。因此只在探针恢复可读后按原240秒边界重跑同一受影响回归，改为实时写raw文件以保证超时输出可保全；无产品修改或测试降级。

## 最终有限 Windows REGRESSION 与冻结

最终命令（前述固定Python/环境不变）：

`PYTHON -B -X utf8 -m pytest -q -p no:cacheprovider scripts/tests/test_restore_archive_request_owner.py scripts/tests/test_recovery_restore_inputs.py scripts/tests/test_restore_archive_catalogue.py doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_archive_catalogue_request_reads.py -k "not linux" --tb=short --basetemp=PRIVATE/stage2b-ordinary-regression-r2/tmp --junitxml=PRIVATE/stage2b-ordinary-regression-r2/junit.xml`

真实pytest exit0、104 PASS/12 deselected/0skip、103.34秒；外层103.641秒，session10536已终止。104=新18 portable+A1原36+当前旧catalogue整文件27+原request-read23。JUnit实际tests104/errors0/failures0/skipped0。原旧fixture已由父另行修复且本轮完整回归包含原三项；我未改该旧文件，不将其旧失败改写成功。六个实现/依赖/测试输入运行前后实际SHA保持。

真实raw stage2b-ordinary-owner-regression-r2.log 341B/SHA256 22519f161bd18b616280cf903b27b35b4a95dad26cd970f8a59e5b5c3ffc084a。独占 PRIVATE/stage2b-ordinary-regression-r2/junit.xml 18475B/SHA256 1748df6a0b74a4a10f319011284354bad1842550e9ba0e62a83a4fa648152e1d；record.json2275B/SHA256 58b1717b261ea543f78d2732247a91d30e4ab5046fbda4cba2456a91661ec1be，记录完整argv、实际exit、输入pins与inputsUnchanged=true。平台探针/collection恢复不说明首次超时根因；旧超时保留不删。

本轮唯一产品/测试文件已验证UTF-8往返一致、无BOM、无行尾空白，内存compile通过。controller精确git diff --check exit0；Git提示现属性将来LF转CRLF，本轮不做额外换行转换。原持久化尾部AST仍原hash。当前冻结：

| 文件 | bytes | SHA256 |
|---|---:|---|
| backend/src/main/resources/recovery_control_restore_catalogue.py | 20980 | 0ad04cef8c57135b8207f416eff802f0bd6b7dbc0e23493dbac1e26965ba56ec |
| scripts/tests/test_restore_archive_request_owner.py（新增） | 17306 | 55ca98e1edb4ac8d241cdf8f825a3fb47b5bf76ace71c821beb62c024929b61a |
| ops/recovery/recovery_restore_inputs.py（原输入，未修改） | 15977 | a1d42136c4cb39f57e119da42416fd97157db0ad7a664bdb8ca4bb0bd65c1ad0 |

| 本 TASK 原始日志 | bytes | SHA256 |
|---|---:|---|
| stage2b-ordinary-owner-red-r1.log | 13126 | 6abc8e8eeb33d8dbc68c7b1bebcecfcdedeb2fb39d2e9d9dc898e53e51aaafc7 |
| stage2b-ordinary-owner-green-r1.log | 242 | 0c13fa73ccda1b0adf8c55612674fe45f080c5c504b9cbf414b3963eb21febda |
| stage2b-ordinary-owner-collection-probe-r1.log | 14285 | 620571dacf8a1c8869eed8598d2d55f87231ee7bc1c9a4a3106ad9ee28427dcb |
| stage2b-ordinary-owner-regression-r2.log | 341 | 22519f161bd18b616280cf903b27b35b4a95dad26cd970f8a59e5b5c3ffc084a |

## 父独立验证与集成界限

交付只有上述controller、新ordinary测试、本独立日志与4份本轮raw logs；不改A1/e633/A2/其它代理文件，未创建worktree/服务或需本子任务清理的进程。正式提交与主任务日志统一由父处理。

12个Linux节点已交父，要求实际POSIX/root custody、无可写祖先的独占basetemp、零skip，使用真实Native.directory及persist，无Windows替代成功。其范围为三目标FULL/2INC六项、三原件tamper三项、identity失效不落盘一项、v2历史三原件闭合一项、0755custody拒绝一项；合并执行新30项即可同时覆盖portable。Linux未终态前不将本范围标为完整completed。

新增真实运行依赖A1当前尚未列入ops/backup_engine/files.json（本轮只读发现）；父所属集成步骤必须加入正式包/控制资源闭包并从实际包验证可导入后才能安装。我不修改该所属文件。此次guard只重复stat已读metadata与观察目录，A1独立核同一有限selected链metadata；/selections目录算法和共享缓存范围不改。本机小链通过不能外推大NAS延迟或实际页面/载荷/来源/目标/clear授权。
