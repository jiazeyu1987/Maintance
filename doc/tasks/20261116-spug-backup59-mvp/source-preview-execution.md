# 空目标准备只依赖来源

目标：修复实际 Spug 选择 `.59` fresh 时旧目标不可达清空备份点、无法准备的问题；准备列表只查询真实来源，真正恢复仍要求新目标准入。

工作树 `C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/integration-worktree`；基线实际安装 `44cc4bb`，开始时工作树干净。前子任务 reset 已实现提交，实际部署由父任务负责；当前仅本地修复，不操作服务器。

经验门禁：沿现有真实选择接口；不伪造列表、不隐藏源错误、不放宽恢复准入；UTF-8、先 BDD/RED 后最小修复及定向回归。长期方案为区分准备选择和恢复目标选择，无 fallback、无临时绕过。

里程碑：RED重现旧目标依赖；最小钩子/READY接线；受影响JS验证及精确提交。当前 ready_for_parent_installation。

- BDD: Given `.59` 尚未准备且旧目标离线，When 用户选择 `.59` fresh，Then 只查询来源备份点，准备可点、恢复不可点。
- BDD: Given 准备历史有匹配的新目标 READY，When 选择该目标，Then 恢复真实目标查询；目标失败仍阻止恢复。
- BDD: Given 来源查询失败，When 读取准备列表，Then 显示错误并阻止准备，不用旧缓存冒充成功。

- RED: 三脚本集成合同在旧目标离线场景仍请求 `targetConfigRef=old-offline-target`，用例失败；补源列表可能含旧目标的场景后恢复按钮错误可点，再次RED。已消费 READY 目标场景仍请求旧目标，第三次RED。
- GREEN: 仅 `.59` fresh 新草稿在没有匹配 READY 或原目标已消费时只请求源。准备模块独立阻止恢复提交，不能因来源列表包含旧目标而解锁；有匹配 READY 则继续真实新目标准入。原操作历史、覆盖模式和其它服务器继续原路径。
- REGRESSION: `node --test ops/spug/smallapp-ui/prepare-target.test.cjs ops/spug/smallapp_ui_safety.test.cjs ops/spug/smallapp_restore_result.test.cjs` -> PASS，90/90，无跳过。集成用例同时证明新目标不可用仍阻止恢复、源错误清空无效选择并明确显示。
- 只改两份产品 JS 与一个现有测试文件；无后端变更、无远端写入。真实页面验收和只替换两 JS 的部署由父任务/安装 agent 执行。
