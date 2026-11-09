# 历史构建证据与安装前工作区门禁分离

## Current Status

in_progress。只读设计已完成，父审阅后批准的独立 A 模块已实现，owner 与父独立各37项真实测试通过。B/C 既有读取器和清理入口尚未接入；实际461/154输入尚未封存。当前闭包还隐含899的461输入及维护仓12输入，实际待清理范围为8个engine加1个资源工作区。完整Spug发布及恢复验收尚未完成，不在本阶段删除任何实际worktree。

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
