# 自动增量备份界面子任务

## Current Status
ready_for_closeout — 已融合核实过的运行界面；自动基线、确认、未知状态跟踪、专用时间预算及源服务恢复回执提示的 83 项 UI 回归，以及 25 项 HTTP/入口/通信合同回归通过。等待主任务集成、提交和真实页面验收，不代表已安装。

## 目标、范围与验证
- 保留运行中五页签、包清单恢复弹框、具体执行桥错误、嵌入 Spug 侧栏的行为。
- 只修改 UI JS、对应测试与本子任务记录，不访问服务器、不登录或派发真实操作。
- 里程碑：界面基线逐文件核对；自动计划和任务跟踪失败测试；最小实现；UI 状态合同回归。
- 使用 Node 状态机单元测试验证；这些测试不代替主任务真实 Playwright 验收。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。计划失败或来源不匹配明确阻止提交；需要全量显示真实 FULL。
- 是否从根因和长期维护角度解决：是。基线由后端验证，浏览器不再按本机历史时间猜测。
- 是否存在临时补丁或绕过：否。后台未知结果只查询原编号，不自动重复 POST。

## 经验门禁
- 多机器来源：主仓 e2e8942 与当前分支的 UI 相同但落后于运行界面，不能用主仓旧 UI 覆盖运行功能。
- 运行来源：已提交 e78b58f 中 app/simple/catalog 等文件；侧栏嵌入资源来自另一个工作区已运行但未提交的 20261104-spug-sidebar-entry 任务，须逐文件校验再融合。
- 本机缺少 D:/ProjectPackage/Int/IntPP/FRONTEND_STYLE.md；本次保持运行版控件布局和样式，仅调整交互和提示；迁移 docs/frontend-development.md 要求保持已有模式。
- 请求失败必须显示；未确认结果保留原请求，自动跟踪不得生成新编号或重复派发。
- 不运行真实 E2E、服务器操作或安装；主任务另行完成相应经验预检和验收。

## API 合同
- GET /incremental-plan?applicationId=... 返回 {applicationId, plan}；plan.schemaVersion=AutomaticIncrementalPlan/v1，state 为 READY / BASELINE_REQUIRED / BLOCKED，包含 sourceConfigRef、reasonCode、parentChainRef、baseFullRef、generationId、chainDepth、pointType、parentPointType、basePointType、finishedAt、baseFinishedAt、evidenceDigest、planDigest。两个摘要均为 64 位小写十六进制；浏览器保留完整计划，服务端验证计划摘要。
- POST /automatic-incremental 请求 {schemaVersion:AutomaticIncrementalRequest/v1, operationId, applicationId, planDigest}；服务端重新验证计划并冻结实际七字段 SmallAppBackupUiRequest/v1 请求。
- READY 执行 INCREMENTAL，BASELINE_REQUIRED 明确确认 FULL，BLOCKED 禁止提交；响应仍为原 public_record，附带 automaticIncrementalPlan。
- 查询继续使用 GET /operations/{原编号}；浏览器本地保留实际冻结请求并验证回执身份。
- 只有 HTTP 409 且 accepted=false、operationId/applicationId 均精确一致的受理前拒绝可解锁草稿。刷新计划后必须重新确认；超时、身份不符或其它失败继续保留原编号。

## BDD 场景
- Given 后端返回 READY 且本地历史缺失；When 选择增量；Then 显示后端已核对的全量基线和最新父点，不读取本机历史猜链。
- Given 计划需要新全量；When 点击备份；Then 确认弹框明确显示全量和原因，只有该计划摘要的明确确认可提交。
- Given 计划被阻断、获取失败或来源不匹配；When 操作界面；Then 显示原因并禁用提交，不复用上次计划。
- Given 切换来源或执行模式时旧计划晚到；When 响应返回；Then 不能覆盖新草稿计划。
- Given 已冻结计划；When 重复点击或计划变化；Then 最多提交一次原 operationId，变化要求重新确认。
- Given POST 与首次查询超时；When 后续轮询或重开页面；Then 持续查询原编号并显示错误，不自动重发 POST。
- Given 后台任务成功或失败；When 完成查询；Then 自动跟踪结束，真实结果可见，下一次增量重新获取计划。

## 执行证据
- 基线只读核对已完成：e78b58f simple.js/app.js/package-catalog.js 与运行文件 Git blob 一致；index.html 的侧栏差异来自原安装脚本的精确复制。
- M1：融合 e78b58f 的 app.js、simple.js/css、package-catalog.js/css、两个目录测试及 UI 安全测试。index.html 与该提交仅差 embedded.js/css 两个引用；原侧栏工作区的 index/embedded 文件与运行版规范化 LF 后逐字一致，只有 Windows 换行差异。未改运行目录、native-ui、入口或安装脚本。
- 基线 SHA256：app.js `d9b1b3b20c47606a1c356debc089e099df18e288d078a64062351d19ca61f5ae`；simple.js `11d4009207eb32311768105d0619ca50feba02e820d49a9eecc47c7cad90069b`；package-catalog.js `85b515816f44da2bc14c6f028a39120251ac454c785d0e7cda4a524ae6b493c1`。
- 基线验证：五组既有测试 67/67 PASS；包括五页签、包清单恢复弹框、替换确认和嵌入登录导航。
- RED：新增 9 项自动计划与结果跟踪测试均按预期失败，包含未请求计划、仍按旧历史选点、无显式 FULL 和缺失轮询。随后精确受理前拒绝、查看旧记录继续跟踪和缺少 evidenceDigest 场景分别先失败。
- GREEN：移除浏览器按 createdAt 猜链，获取并冻结后端计划，按真实 FULL/INCREMENTAL 确认提交；晚到响应、重复点击、过期计划、未知结果及旧历史查看均验证通过。
- REGRESSION：`node --test ops/spug/smallapp_ui_safety.test.cjs ops/spug/smallapp_restore_result.test.cjs ops/spug/smallapp-ui/package-catalog.test.cjs ops/spug/smallapp-ui/package-catalog-dialog.test.cjs ops/spug/smallapp-ui/embedded.test.cjs` → **82 passed / 0 failed / 0 skipped**。
- 对齐后端实际原因码：8 种 BASELINE_REQUIRED 明确说明全量原因；BLOCKED 保留原错误码并给出中文解释，未知严格元数据错误仍阻断，不自动改全量。新增实时来源检查的 7 种中文原因映射先以单测复现只有泛化提示，再补齐后验证通过。
- 当前无真实登录、备份、恢复、服务器安装或版本提交；由主任务负责后续集成验收。

## 本机 HTTP 合同补充
- 范围：只新增 `ops/spug/test_automatic_incremental_http.py`，真实启动 entry.handler 的本机 ThreadingHTTPServer 与仅提供计划/选择响应的本机执行桥 fixture。真实 HTTP、请求解析、计划摘要、临时预约文件、OS 锁与派发认领均保留；Django 用户/任务模型明确隔离，业务执行适配器记录调用后拒绝执行。这不是浏览器 E2E，也不证明备份执行成功。
- BDD: Given 已登记来源及 READY 计划；When 真实 GET 计划；Then 返回已验证计划，执行桥仅收到所选来源的 `/incremental-plan` 请求。
- BDD: Given 页面计划过期；When 真实 POST；Then HTTP 409 精确返回当前 ID 的 accepted=false，临时预约目录无该原件。
- BDD: Given 当前计划；When 首次 POST；Then HTTP 202、真实临时预约和一次派发认领；业务执行被隔离适配器明确拒绝，不能产生备份成功结果。
- BDD: Given 原 ID 已预约且后端已有新计划；When 重发同一意图；Then 只查原件，不重新选计划或再次派发。
- BDD: Given 受理过程出现未知异常；When 原件尚未/已经落盘；Then HTTP 500 均不得声明 accepted=false。
- BDD: Given 不同来源、目标绑定或非登记选择地址；When HttpBridge 请求增量计划；Then 请求前拒绝，不访问其它 endpoint。
- RED 方案：只读提取 Git HEAD 的旧 entry/adapter 到系统临时目录，在旧路由上运行计划查询及过期 POST 场景，证明旧实现缺少 HTTP 合同；随后使用当前源码验证 GREEN。不修改产品源码或运行目录。
- RED：实际提取 `0c5828a` 的 entry/adapter 执行两项真实 HTTP 测试，GET 计划和 POST 过期请求均返回 `409 ENTRY_ROUTE_UNKNOWN`；分别缺少预期 `200` 和精确未受理证明，**2 failed**。临时副本自动清理，没有修改产品源码。
- RED：当前入口实际 HTTP 回归最初 **9 passed / 1 failed**；同 ID 重发前将 fixture 手动模板变更后错误返回 `409 SPUG_MANUAL_TEMPLATE_CHANGED`，无法查询原件。根 Agent 已修复授权后的原件优先查询，本子任务未修改 entry 产品文件。
- GREEN / REGRESSION：在 `ops/spug` 运行 `python -X utf8 -m unittest test_automatic_incremental_http test_automatic_incremental_entry test_smallapp_bridge_errors -v` → **25 passed / 0 failed**（其中真实本机 HTTP 10 项）。解释器为 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`。
- 真实派发边界证据：预约持久化后原 dispatch 认领为 DISPATCHING，隔离执行适配器记录一次命令并明确抛出禁止业务执行，原件记录 `SPUG_DISPATCH_OR_HISTORY_FAILED`，无业务历史或备份成功状态。重复 ID 保留原计划、不重新访问计划 endpoint、不再调用执行适配器。

## 自动增量请求时间预算
- 后台计划新增 30 秒整体预算，执行桥专用请求为 40 秒；浏览器仅 GET `/incremental-plan` 和 POST `/automatic-incremental` 使用 60 秒整体 deadline，其它请求保持 20 秒。计时覆盖 fetch 和响应正文读取，结束后清理计时器，不做无限等待或自动重试 POST。
- BDD: Given 请求方法与路由；When 创建页面请求；Then 只有上述两个方法/路由组合使用 60 秒，其它仍为 20 秒。
- BDD: Given 请求头已返回但响应正文未结束；When 整体 deadline 到达；Then 仍能中止读取并显示超时，不能在读正文前清理计时器。
- BDD: Given 自动增量 POST 超时且原编号查询也失败；When 超时处理结束；Then 保留同一原件、显示错误，后续仅查询原编号，不重复 POST。
- BDD: Given 后台返回 INCREMENTAL_PLAN_TIMEOUT；When 展示计划错误；Then 显示中文核对超时原因并禁止提交。
- RED：4 项新增测试在原实现上全部按预期失败：实际计时器均为 20 秒而非专用 60 秒，后台计划超时仅显示泛化提示。
- GREEN：生产 `api()` 精确按方法和路径选择时间预算，保持同一个 AbortController 覆盖 fetch 与 json 读取；通过原始 api 函数及受控计时器验证中止和 finally 清理。自动提交超时后的原件 GET 与 progress GET 均继续使用 20 秒，持久化实际请求不变，只产生一次 POST。
- REGRESSION：完整 UI 五组测试 **82 passed / 0 failed / 0 skipped**；`git diff --check` 通过。
- 集成提醒：只读检查发现 `ops/spug/smallapp-entry.locations.conf` 的通用代理仍为 `proxy_read_timeout 30s`，已报告根 Agent 处理自动路由的完整代理预算；本子任务未修改 Nginx 或运行配置。

## 源服务恢复回执提示补充
- BDD: Given 后台因源服务恢复回执缺失或与原备份不匹配而返回 BLOCKED / INCREMENTAL_SOURCE_RESTORATION_INVALID；When 页面取得计划并尝试提交；Then 明确提示检查源服务恢复记录，保留原错误码并禁止提交，不建议改为全量绕过。
- 范围：只在既有 app.js 统一原因映射补充中文说明，沿用现有 BLOCKED 禁止提交行为；新增原 UI 状态测试后按 RED→GREEN→REGRESSION 验证。
- RED：`node --test --test-name-pattern "missing source restoration proof" ops/spug/smallapp_ui_safety.test.cjs` → 1 failed，实际仅显示“尚未满足执行条件（INCREMENTAL_SOURCE_RESTORATION_INVALID）”，缺少具体恢复回执原因。
- GREEN：在 app.js 现有 reasons 中增加中文映射后，同一用例 1 passed；同时断言提交被禁用、无确认弹框、无 POST、没有全量替代提示。
- REGRESSION：完整 UI 五组测试 **83 passed / 0 failed / 0 skipped**；受影响产品文件 `git diff --check` 通过。
- 冻结：2026-11-08 01:08:43 北京时间，产品变更限 app.js 与原 smallapp_ui_safety.test.cjs；供根 Agent 纳入最终实现提交。未修改 simple.js、后端或运行文件。
- 提交门禁报告：`automatic-incremental-ui-regression.json`；原始 TAP：`automatic-incremental-ui-regression.tap`。为形成可核对的报告实际重新执行五组测试，83/83 PASS；报告包含受测界面资源及测试的工作区原始字节 SHA256，供提交前精确核对。
