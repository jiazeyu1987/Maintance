# 执行记录

## 用户需求
评审备份恢复 6 个 Milestone 是否正确。

## 授权与范围
只读评审；不执行真实备份、恢复、部署、服务器访问或数据写入。

## 评审依据
- 已读取用户贴出的 6 个 Milestone 文本。
- 已读取 `E:\IntRuoyi\docs\release-backup-restore.md`、灾备技能说明及 `references/recovery-contract.md`。
- 结合现有 `backup-ops`、备份计划页、运行控制台和此前形成的测试服备份恢复方案进行交叉判断。
- GREEN: experience-preflight -> PASS；本任务不执行高风险动作。

## 评审结果

- PASS: M2 全量备份+全量恢复放入第一版是正确的；只有备份文件没有隔离恢复不能形成恢复基线。
- PASS: M3 真实增量和 `FULL -> I1 -> I2 -> I3` 整链恢复放入第一版是正确的；对于几百 GB 数据，不能延期到后续优化。
- PASS: M4 作为页面入口和安全操作流，放在底层能力之后是正确的。
- PASS: M5 覆盖升级、降级、换机、换盘、换 IP/域名、跨架构和历史版本，是必要的兼容性放行门。
- PASS: M6 覆盖调度、容量、保留、故障注入、最长链恢复和最终验收，是长期运行放行门。
- ADJUST: M1 必须明确独立于业务后端的恢复控制平面；当前业务后端停止时，不能依赖同一个后端查看 operation 或发起恢复。
- ADJUST: M1 必须通过实测决定逻辑备份或物理备份主方案；几百 GB 下不能默认逻辑 dump 一定满足停写、恢复时间和空间目标。
- ADJUST: M4 的“两个按钮”必须在后端区分恢复演练与覆盖当前测试服；产品可以只有两个主入口，但恢复按钮内部必须先选“仅演练”或“受控替换”。
- ADJUST: M5 不应承诺任意历史版本自动恢复，应交付明确支持矩阵和不兼容阻断。
- ADJUST: M6 不是只在最后才考虑容量和监控；M1 建模、M2/M3 实测、M6 做持续运行验证。

## 推荐顺序

1. M1：范围、资产、owner、RTO/RPO、容量、恢复控制平面、数据库主方案和一致性方案。
2. M2：实际数据规模 FULL + 隔离全量恢复。
3. M3：实际数据规模真实增量 + 连续链恢复 + 损坏链阻断。
4. M4：异步 operation、候选选择、恢复演练、受控替换和证据页面。
5. M5：支持矩阵、同架构换机、历史版本恢复和不兼容阻断。
6. M6：调度、保留、容量、故障注入、最长链恢复和最终放行。

## 结论边界

- M1-M3 完成：具备可验证的底层备份恢复能力。
- M4 完成：具备受控按钮入口，不等于可以长期运行。
- M5-M6 完成：才可以对“几百 GB、升级降级、换硬件等场景下可持续恢复”作第一版放行结论。

## 验证与收尾

- GREEN: UTF-8 复读评审任务、经验索引和现有备份恢复规则 -> PASS。
- GREEN: `git diff --check` 维护仓与 `E:\IntRuoyi` 相关文档 -> PASS，无 whitespace error；仅 LF/CRLF 规范化提示。
- GREEN: `rg -n` 新增大数据量里程碑关键词路由 -> PASS。
- GREEN: `task_closeout.py --task-id 20260918-backup-restore-milestone-review --mode preview` -> PASS，delete none，blocked none。
- GREEN: `task_closeout.py --task-id 20260918-backup-restore-milestone-review --mode apply` -> PASS，deleted none，linked worktree false。
- Experience: 已更新既有 `E:\IntRuoyi\docs\release-backup-restore.md#大数据量备份恢复首版里程碑顺序门禁`，同步更新 `docs/experience-index.md`；未新建长期经验文件。
