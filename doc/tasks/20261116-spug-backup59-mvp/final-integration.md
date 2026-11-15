# 备份服 MVP 最终融合准备

## 目标与当前状态

将已部署集成分支本任务后续增量迁入当前 int_main 基线的独立工作区。只准备可审查提交，不部署、不合入主线、不清理工作区。当前状态：in_progress；真实完整/增量验收未完成。

## 固定输入与里程碑

- 主线基线：25fe7edc47ee1cba9a4b85bcdc892d7819ea107e。
- 任务来源：bcaf0e3f2efe48c455195307a94703ffedd1b813，相对已融合首版按钮对应集成提交0bbf939的增量。
- 工作区：C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/final-integration。
- 一次迁入最终差异，手工解决standard_fixes.py与smallapp_entry.py，保持主线其他修复；最终结果运行必要定向集，再提交供父审。

## 经验门禁

- 已读docs/worktree-memory.md和docs/worktree-restrictions.md：专用工作区、固定提交、精确任务文件；保留int_main脏日志和其它并发任务。
- 禁止整branch merge或复制部署基线的额外修复；无法精确分离时报告具体语义冲突。
- 全量和增量真实验收前不得合主线或删除任何worktree。
- GREEN: experience-preflight -> PASS（仅本地独立融合准备）。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，回归主线并保持任务实现合同。
- 是否存在临时补丁或绕过：否。

## BDD与验证

Given 主线已有首版准备入口与独立任务修复，When 迁入已验证的备份服空目标/恢复去重增量，Then 入口保留主线语义，仅新增本任务正式能力，不导入部署基线上其他线程的改动。

既有实现RED/GREEN记录随本任务差异迁入；融合不重新发明行为，最终在融合结果运行相关定向回归。主线文件不作为测试/部署输入。

## 融合结果与验证证据

- 一次应用 `git diff --binary 0bbf939 bcaf0e3 | git apply --3way --index`（实际通过Python bytes传递，不经文本管道）只产生两个冲突。
- standard_fixes.py仅加入本任务三个transform调用；没有带入部署基线的supervisor、preservation_readback_process、minimal_input_diagnostics改动。
- smallapp_entry.py只增加fresh_prepared与旧目标历史跳过条件，保留int_main自身reserve_locked及automatic_context行为，没有带入另一线程takeover_admission分支。
- 首次Linux载体因Windows .git链接不能在容器内解析而失败，修正为显式只读挂载Git目录及GIT_DIR/GIT_COMMON_DIR/GIT_WORK_TREE，未修改产品或依赖。
- Spug后端46/46、页面82/82、计数辅助2/2通过。Linux定向11通过，唯一构建allowlist失败经主线原HEAD25fe7ed的standard_fixes与原测试在本独立工作区复现相同10项，证明主线已生成但测试清单遗漏。
- 经父批准，仅补齐10个已存在主线模块的构建合同allowlist；该单测复跑1/1通过。总计Linux12项已通过，没有扩大测试矩阵或增加产品变化。
- 后续父要求准备sql-readback最小合同修复，由实现Agent在原integration完成；本次先提交可审查融合结果，收到后续提交后仅迁入增量并复跑受影响集。未部署、未合主线、未清理。

当前状态：ready_for_review；尚待v12后续增量和实际完整/增量验收，不能标记整个任务completed。

## v12 增量融合

- 来源正式HEAD31a670f883054a0cf09c4241a781327f117af46e，bcaf0e3之后仅实现d6ec93c和验证记录两提交。精确三文件增量：standard_fixes.py、test_prepared_database_readback.py、database-readback-review.md，三方应用无冲突。
- prepared数据库路径仅实际导入及SELECT1，同操作同目标连续链消费；未执行的全库数据摘要明确false/NOT_PERFORMED，不伪造证明。
- GREEN: 同一现有隔离Linux载体运行test_prepared_database_readback.py -> 4/4 PASS，未重复既有已通过组。
- 发布独立release-v12已固定该提交，默认只读预检输出ACTIVE；没有安装/停止服务。父随后确认真实恢复因容器健康检查失败且active保留，暂停v12发布，等待健康检查最终修复。此融合工作区继续保留，未合入主线。
