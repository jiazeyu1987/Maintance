# 空目标准备入口UI

## 目标与状态
- 实现固定.59的准备入口、清理范围确认、三阶段进度与历史查询，遵守父任务接口。状态 ready_for_parent_review；本子任务无独立合并、清理或提交。
- 仅修改index.html、独立prepare-target.js及其测试/样式；无远端动作、不改后端、不提交。
## 经验门禁
- 显式UTF-8读写；先BDD/RED，再实现及回归。复用现有api鉴权和Spug样式；指定D盘样式文件经父agent核缺失，不重新设计页面。
- 未配置显示真实错误，未知提交保留原编号仅查询；不以单测响应替代真实环境READY，不在页面暴露凭据。
## 设计约束检查
- fallback/降级/吞异常：否；长期可维护：是，独立小模块复用现有API；临时绕过：否。
## BDD
- Given选择备份服及备份点，When准备，Then展示后端预览清理/保留范围，确认后一次提交。
- Given网络响应未知或刷新，When再次操作，Then查询原编号而不重复清理。
- Given配置缺失/阶段失败，When读取，Then明确显示原因和阶段。
- Given后端READY，When查询，Then显示空目标就绪并刷新可恢复配置；其它状态不能显示成功。

- RED：Node UI状态合同7例，其中6例因未实现状态/预览/派发失败、1例目标拒绝通过；先运行缺模块失败仅记载体，再用空实现确认行为RED。
- GREEN：实现独立prepare-target模块后7例通过；非真实服务器E2E。
- BDD：Given 已转入进度页，When 提交或原任务查询网络失败，Then 进度页显示错误原因而不是只在隐藏表单显示。RED：补充 CONNECTION_LOST 断言后 6/7 通过、该例失败；GREEN：显示进度错误后 7/7 通过。
- BDD：Given .59 尚未登记空目标，When 在真实 app.js + simple.js 脚本上下文选择 .59，Then 可预览准备范围，普通恢复仍禁用。RED：集成合同 7/8 通过、.59 选项仍禁用；GREEN：新模块渲染钩子保留 .59 准备选择后 8/8 通过。没有修改原恢复准入合同。
- REGRESSION：`node --test ops/spug/smallapp-ui/prepare-target.test.cjs ops/spug/smallapp_ui_safety.test.cjs ops/spug/smallapp_restore_result.test.cjs` -> PASS，84/84，无跳过。
- GREEN：`node --check ops/spug/smallapp-ui/prepare-target.js`、相关文件 `git diff --check` -> PASS；四个 UI 文件经 Python 严格 UTF-8 解码且无 BOM。
- 本地改动：index.html、新 prepare-target.js/.css/.test.cjs；本日志。安装资源清单由父 agent 更新，需要包含 JS/CSS。
- 真实服务 E2E、部署及远端清理未执行，单元及脚本集成合同不代表远端 READY。后台、鉴权、运行进程及部署集成由父任务完成。

## 2026-11-16 预览超时接线
- 状态 ready_for_parent_review。父任务要求仅在 app.js 将 POST `/prepare-target/preview` 的浏览器超时设为 85000ms，对应后台预览 75 秒预算与网关 80 秒；其他计划/选择 60000ms、普通请求 20000ms 不变。追加范围为 app.js 及 smallapp_ui_safety.test.cjs。
- BDD：Given 准备预览可能使用完整后台预算，When POST 精确预览路径，Then 使用 85 秒超时；GET 同路径、相似路径和准备提交仍使用 20 秒，原计划与选择超时保持不变。
- 设计约束沿用上述检查：无降级、吞异常或临时绕过；有界超时与正式上游预算对齐。
- RED：`node --test --test-name-pattern="only prepare preview POST" ops/spug/smallapp_ui_safety.test.cjs` -> FAIL，实际 20000ms、不等于要求的 85000ms。
- GREEN / REGRESSION：原 84 例集合加新断言，`node --test ops/spug/smallapp-ui/prepare-target.test.cjs ops/spug/smallapp_ui_safety.test.cjs ops/spug/smallapp_restore_result.test.cjs` -> PASS，85/85，无跳过。
- GREEN：app.js 语法、两处代码 diff 检查及严格 UTF-8 重读通过；未提交，未执行远端操作。
