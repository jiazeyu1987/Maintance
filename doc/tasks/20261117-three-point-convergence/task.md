# 发布备份恢复三项收敛
## Goal
实现发布后备份来源同步；空目标准备自动携带版本依赖和存储策略；收尾长路径清理及重复读取精简。不增加业务功能。上一任务20261117-sixstep-repeat已completed。
## Milestones
- [x] 核实当前代码及最小边界
- [x] 三项BDD/RED/GREEN与必要回归
- [x] 集成验证、提交和收尾
## Expected Verification
真实发布结果可驱动来源更新且失败不得假成功；新备份点准备依赖完整且来源不可漂移；清理仅本任务路径；重复读取减少但内容变化仍拒绝。先本机实现，未授权的新服务器写入不执行。
## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，接入正式入口而非任务私有补救脚本。
- 是否存在临时补丁或绕过：否。
## 经验门禁
Trigger：发布/恢复流程修复及重构。Preflight check：实际入口、运行包与源码关系、Git归属和既有脏文件、链与配置pin、路径边界。Blocker：配置身份不明、并发覆盖、实际依赖缺失。Verification：BDD和RED->GREEN->REGRESSION，实际入口集成验证，内容漂移拒绝。Forbidden action：不改生产NAS、不绕过校验、不混入其他改动、不以单测代称已部署。Evidence：本任务execution-log及上一轮验收报告。
## Current Status
completed：三项本机实现及必要验证完成，已合回 int_main，本任务临时 worktree 已删除。未部署服务器；上线需配置真实来源绑定并执行发布验收。

## Implementation and evidence
- 发布：finish_reopen 正常服务健康后生成并激活新备份来源；显式 profile，失败传播并保留同候选重试身份。普通未配置服务器不猜路径。
- 恢复：版本元数据使用归档副本，附件策略沿 owner 的固定父链继承；保留身份和 SHA 检查。
- 清理/去重：已融合任务 worktree 走长路径清理和外置归属回执；单次 chain 每点完整 load 一次，无跨阶段缓存。
- Linux 实际双包回归 37 PASS；Windows 清理与恢复组合 90 PASS；准备 55 PASS；chain 行为 3 PASS；发布入口 24 PASS。来源激活边界测试另见 source-sync-log.md。
- 真实文件、SHA、Git worktree、长路径和 Linux flock/proc 已验证；systemd/Docker 激活边界为单元测试替身，未执行线上发布或恢复，不以本机测试替代线上验收。

## Workspace
- 本次路径：C:/SpugHandoff/converge-20261117
- 分支：codex/three-point-convergence-20261117
- 基线：3f4a62e9d15e6566e65b87515b64ab898b84be7b
- 不构建业务发布包；封包构造由 scripts/tests/test_backup_variants.py 验证。
- 验证命令及分项 RED/GREEN：本目录 execution-log.md、source-sync-log.md、target-dependencies-log.md、readback-log.md、cleanup-log.md。
- 实现提交 a76286f；融合提交 13769c3；清理回执修正 4148683。全部已合回 int_main，主线融合后 91 项测试通过，最后回执修正的真实长路径清理用例再次通过。
- 清理结果：cleanup-result.json 为 passed，Git 登记与物理路径均不存在；cleanup-proof.json 保留删除前归属回执。4908 个跟踪文件核对通过。本次未启动或修改业务控制台，不涉及控制台路径恢复。
- 融合前后原主线 diff/status 摘要一致，无关脏改动保留；最终日志仅精确提交本任务追加段落。
