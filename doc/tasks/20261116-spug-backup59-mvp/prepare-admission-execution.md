# 准备准入只保留当前互斥

目标：修复真实页面准备被旧恢复记录不可达阻断；本次明确未受理拒绝不再误记执行UNKNOWN，不把404或超时当远端已停止。

工作树 integration-worktree，基线1bea149，开始时干净。仅本地实现，安装和真实主机执行由父任务负责。

经验门禁：BDD/RED/GREEN；沿原source submission lock和native宿主lock/active预约；不修改旧恢复历史、不补旧成功、不解除活动锁；固定.59，保留NAS。显式UTF-8、精确提交。设计约束：无fallback/吞异常，根因是历史可达性被错当运行互斥，无临时绕过。

## 实际定位
- 实际容器 `intruoyi-spug-transfer-spug-1`，本次 `prepare-5b48923e-c05f-49c9-896b-ab1924f65aba` 本机记录不存在，准备记录总数0。
- 当前历史gate首个无终态命中 `smallapp-afdb2b25c4334477a40969587d44af0d`，2026-10-25T11:12:53Z，目标 `intruoyi-59-int07-fast-20261025-r1`。journal存在，lastResult为RUNNING，terminal不存在；真实最新观测2026-11-15T17:54:50.938083Z为RUNNING/BRIDGE_NETWORK_UNREACHABLE。因此本次busy来自旧路由不可达，未启动本次native执行。
- native准备持 `/var/lib/spug-restore-resources/lock` 到结束并在开始拒绝active.json；现有恢复reserve使用同一路径lock+active.json。本机新准备保留源提交锁与prepare ACTIVE；新RESTORE仍经block_while_preparing。已派发但延迟的旧请求在准备期间不能预约宿主，清理停旧control后旧引用不能进入新控制配置。
- 父任务最近远端实际无worker/active证据为私密 `spug-backup59-mvp-20261116/network-before-prepare.private.json`；后续必要端口安装回执 `firewall43059-installed.private.json`。本子任务不重复扫服务器或修改活动锁。

## BDD
- Given 历史恢复无journal或路由不可达而本机无当前准备，When 准备，Then 不查询旧历史，预约本次原生执行；实际宿主互斥仍由原生执行拒绝。
- Given 准备提交收到精确409/PREPARATION_TARGET_BUSY，When 页面处理响应，Then 显示“未受理”并清除本次provisional；该错误只在本机预约前发出。
- Given 响应超时、网络错误或其它拒绝，When 页面处理，Then 保留原UNKNOWN和编号，不声称未受理。

状态 ready_for_parent_installation。

- RED: 历史恢复缺journal用例失败PREPARATION_TARGET_BUSY；UI明确busy响应仍blocked用例失败。
- GREEN: 删除准备入口历史恢复查询整段；本机prepare当前互斥与原生宿主互斥保留。仅精确busy拒绝清本次未受理草稿；不兼容已保存的旧浏览器未知状态，不新增封闭/接管协议。
- REGRESSION: `python -X utf8 -m unittest test_prepare_target test_prepare_target_http test_prepare_target_native -q` -> PASS，31/31；定向三份JS测试 -> PASS，91/91。无全仓测试，无远端写入或旧历史修复。
