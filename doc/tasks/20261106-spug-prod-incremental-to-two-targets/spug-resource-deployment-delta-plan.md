# Spug 已提交资源与实际安装差异

## Current Status

in_progress。第二次真实只读观察已终止，返回 MAIN_RESOURCE_NON_ADAPTER_RESOURCE_CHANGED；applyRequested=false，未创建安装 attempt。当前安装器错误地把单次 Git 提交的 changedFiles 当作相对现网的完整安装差异。实际候选 c7728ad 包含此前 73c0e72 已提交的历史备份恢复入口变化，现网仍缺少 app.js 与 simple.js 两项。

## 目标、里程碑与预期验证

保留原 MainProgramSpugResourceBuild/v1 原件及其 changedFiles 语义，新增显式安装差异合同，允许安装已审阅、已提交、已测试的 adapter 与两份 UI 资源。原 11 项资源构建和 154 项测试输入仍逐项核验；安装差异不能授权任意未知文件。原失败证据不改写。重构按 AGENTS.md 的 Subagent-Driven Development 执行。

1. 核对实际三个差异及产品提交归属；原 build/test 报告保持。
2. 先写 BDD/真实 RED，再最小实现显式安装差异、逐文件原件保全及失败状态记录；默认 prepare 不写运行资源。
3. 父任务独立验证新增与受影响回归、限定提交；生成新的安装输入和差异文件，不修改旧 build 报告。
4. 新鲜完整只读观察、逐文件原 SHA 比较、授权范围内安装、精确 entry 重载和完整安装后核验。三配置、连接、历史、其他八项产品资源、容器及 18081 保持。

## 已审阅产品行为

- smallapp_adapter.py：c7728ad 的独立目录来源绑定。
- smallapp-ui/app.js：历史来源仅允许恢复；明确历史链身份、父点与隔离错误提示。
- smallapp-ui/simple.js：全部包清单恢复按钮按 catalogueRestoreBindings 找到登记的历史来源，随后绑定对应应用、服务器及安全模式。
- 两份 UI 变化来自 73c0e72，属于用户要求“全部全量/增量可选择恢复”的原范围；不新增页面或测试控件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。旧 v1 保持仅 adapter 规则；新 v2 必须提供显式固定 before/after pins 的安装差异，缺件或未知变化即拒绝。
- 是否从根因和长期维护角度解决：是。区分 Git 提交差异与当前运行资源安装差异，不再把二者混用。
- 是否存在临时补丁或绕过：否。不跳过其余资源、构建、测试、进程身份或历史保全核验。

## BDD 与 TDD 要求

- Given 已提交候选与现网仅有明确登记的三项差异，When v2 prepare/apply，Then 三项安装且其余八项保持；新 entry 加载预期模块。
- Given 缺少差异 pin、重复/越界路径、before 与现场不同或 after 与构建不同，When prepare/apply，Then 写入前拒绝。
- Given 第二项替换失败或写入后回读失败，When 派发结束，Then 保留全部原件、逐文件真实变化状态与失败原件，不自动重试、回滚或声称无写入。
- Given 原 v1 只有 adapter 差异，When 原调用执行，Then 原合同仍通过；出现其它差异仍拒绝。
- Given 只读观察失败，Then 保留原始观察或传输证据，不生成有效观察 PASS 或安装成功。
- RED -> GREEN -> REGRESSION 真实输出写专属 tdd-log；单元 fixture 不冒充实际安装。

## 经验门禁

- Trigger：已提交产品候选与实际安装资源不一致。
- Preflight check：明确 11 项资源和安装差异，保留原 build/test 与失败原件；新观察无未知进程或 attempt；写前记录 experience-preflight。
- Blocker：任何未登记差异、原 SHA 漂移、构建/测试不足、实例身份不明或未知尝试。
- Verification：真实失败测试、父独立回归、实际前后资源/模块/原行为核验；完整三来源与三目标 UI 验收仍单独执行。
- Forbidden action：不得把 changedFiles 改成三项后覆盖旧报告，不重启 Docker/WSL/整个容器，不修改业务或 NAS，不用局部观察冒充完整观察。
- Evidence：spug-resource-build-c7728ad.json；spug-resource-validation-c7728ad.json；PRIVATE/spug-resource-observe-after45-second.stdout.private.log（107 B，SHA ca0d03551f75de1d69626ea70cf74163bccf2b62bf2803c1a3be7b12d086c0f1）。
