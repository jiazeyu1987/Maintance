# 历史构建证据与安装前工作区门禁分离

## Current Status

in_progress。独立 A 模块 owner 与父各37项真实测试通过；实际 899/45/c772 的650个逻辑输入、649条原路径已封存，owner完整读回及父独立650项字节/SHA读回均通过。父验证显式禁止读取原输入路径，实际读取次数为0；未删除真实工作区。B/C既有读取器与清理入口尚未接入。实际待清理范围仍为8个engine加1个资源工作区；完整Spug发布及恢复验收尚未完成。

## 目标、里程碑和预期验证

采用Subagent-Driven Development评估正式历史证据读取与安装前干净checkout检查的职责边界。已完成安装的历史验证应可持续核原提交、原包、原构建/测试及实际安装原件，不能以长期保留临时发布worktree维持验证；新的安装prepare仍必须核原提交对应专属干净工作区，不得因历史读取能力跳过安装前门禁。

1. 子代理先只读追踪coverage、generation、published_resource_evidence、旧automatic阶段及closeout读取器的全部临时worktree依赖，列出准确消费者与实际既有归档内容。
2. 提供最小正式合同设计、BDD场景、受影响文件和验证命令；父确认具体设计后才进入RED与实现。最初只读授权止于此；父完整审阅 assessment 后明确批准 A 阶段独立模块、测试及专属日志，B/C 继续冻结，避免正在进行的 Spug 观察/安装输入漂移。
3. 后续实现须真实临时Git仓库/已提交blob/包/文件的RED→GREEN→REGRESSION，覆盖checkout删除后的历史验证，以及缺件/漂移/伪造成功拒绝。实际归档和删除另按经验门禁执行。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。历史与安装操作显式区分，缺正式持久证据即拒绝，不按文件不存在自动放行。
- 是否从根因和长期维护角度解决：是。临时构建输入与不可变历史证据拥有独立生命周期，原始字节和结果语义保留。
- 是否存在临时补丁或绕过：否。不保留空壳worktree、不替换路径链接、不修改旧pin或复制不明Git模板。

## 经验门禁

- Trigger：已完成控制安装后prepare/历史reader仍引用临时发布worktree，最终收尾必须清理本任务工作区。
- Preflight check：只读固定当前实际generation闭包、owned-builds与已有cleanup原件，核哪些路径已删除、哪些仍消费者引用；读取worktree-memory中的任务归属、持久证据、合并后验证和清理规则。
- Blocker：依赖无法枚举、原件丢失、当前/历史语义未区分、拟重写原SHA或弱化安装门禁。
- Verification：实际Git与文件载体；历史原件缺失必须FAIL，新安装缺checkout必须FAIL；完成后还需本任务实际持久证据与合并验证。
- Forbidden action：不删除/移动工作区，不改旧报告、失败/成功原件、服务器或运行配置，不在本阶段把设计或fixture当正式清理成功。
- Evidence：main-program-control-generation-45dd7dc-r6.json、main-program-four-controls-activation-milestone-45-r6.json、task-owned-builds.json、已有owned-build-cleanup报告和本次独立设计记录。

## 2026-11-10 A阶段真实输入封存范围
允许已提交且父37项验证通过的 HistoricalBuildCustody A 模块，在原临时构建工作区仍保持当前状态时，正式准备并封存已枚举的899/45/c772原构建与测试输入。先生成独占显式inputs并逐项核原报告和原路径字节；任一不符即保留失败并报告，不改原报告、pin、worktree或源码。仅可在本任务PRIVATE下创建独占 historical-build-custody-* 目录及载体/原件，公开报告只能无秘密的计数/SHA/范围。不得将缺失文件由Git内容替代为历史原始字节；Git仅验证原字节与目标提交关系。B/C依然冻结；不删除/移动/改worktree，不安装或发布。
前置核验：现有A实现与37项父验证固定、mapped worktree-memory已核保全与任务归属门禁，精确三工作区与原报告，不递归扫描PRIVATE或无关主工作区。运行使用显式UTF8，真实封存只证明原字节托管，不冒充测试、安装或清理通过。
GREEN: experience-preflight -> PASS。此范围仅本机已授权任务输入保全；缺件或漂移必须停在明确原因，禁止默默弱化完整集合。

## A阶段实际结果

- 真实封存退出0、21.0秒，四组输入分别461/23/12/154项，650逻辑引用共11,244,744字节；原路径649，按内容去重498项。
- `historical-build-inputs-899-45-c772-r1.json` 固定全部原件；PRIVATE归档9,349,120字节，SHA256 `92388d1857b790f8ba9f8d3a53976b5af9434f9a23e9be6bc4e14246ee588ac1`。
- 父独立验证实际退出0、0.969秒，重读650引用共11,244,744字节，原输入路径读取门禁触发0次；结果 `historical-build-inputs-parent-verification-r1.json` 3924字节，SHA256 `7a83c7b1c2d57f73ad043ed77b05a6903ee1addadd8af65015a502b7e166f113`。
- 以上只证明持久原始字节与Git/原报告关系，不证明安装、恢复或实际工作区删除；原报告、原pin、工作区和B/C保持。
