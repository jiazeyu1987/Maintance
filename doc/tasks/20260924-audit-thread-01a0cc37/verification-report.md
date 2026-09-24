# 指定发布任务执行方式审查

证据时间：2026-09-24 09:47–09:57 +08:00。目标 threadId：01a0cc37-64b1-7132-83ba-1e6bef6ac76e。当前会话没有 read_thread 工具，已按精确 id 读取两份本机 rollout；较新的续接文件最后记录为 09:42 turn_aborted。

## 结论
该任务在推进批准版本的按钮化发布，当前在测试服部署获取锁阶段失败。遇锁后停止写入、只读查 owner，不强行清锁或继续正式发布，这个方向正确；但不能把本次问题简单归因为“其他任务占锁”。发布器锁 SQL 存在明显赋值顺序风险，且当前锁错误显示的 operation/releaseTag 恰好是本次发布，需优先复现该代码路径。同时，任务状态记录滞后及明文凭据记录是已确认问题。

## 授权和实际阶段
- 原始任务先整改旧 migration 不可变、supersession、allowedPublishScopes 和依赖合同，经历多轮 NO-GO。后续 R22 已明确同意仅使用应用 b15b52e0c4c14ed46ebe0772ba4aea2caa8df090、维护 2a867b91c9add6ec681831e927b347d2e7b088bf 进入新的按钮化发布链路。
- 在 2026-09-23 18:24 的原始用户消息中可追溯上述精确 GO；R2 workflow 创建时间为 2026-09-24 01:59，本次构建在 GO 之后。releaseTag 的日期不能直接当作本机时区时间推断授权先后。
- R2 应用和维护 worktree 的 HEAD 与上述批准值相同，git status 均干净；workflow 的 application/frontend/maintenance 三角色提交也一致。
- 发布 tag：release-20260923-175920-9e66dcb4e9e6-app；workflowId：rw-9e66dcb4e9e6。
- 构建已形成 READY 包并保留双摘要：packageDigest=8083ba5309998dad4d67c72cf5d5158461d2112c9ccf4ebacc4c8c3b792ebca5；manifestDigest=dd246eec3ac46a0789d83e2d6e068f8b5214287ce28e64e8964eb0a36e1165d4。
- 用户随后明确允许本次使用芋道源码/admin 进行发布操作员和页面验收，不能沿用此前缺少测试租户凭据的 blocker；这不等于额外授权修改不相关业务数据。
- 09:23:42 页面提交 publish-test operation d9764032-753b-49fd-8014-f4a05cb39d34。09:24 workflow 已 FAILED，failedStage=TEST_DEPLOYING、errorCode=RELEASE_WORKFLOW_TEST_DEPLOYING_FAILED，operation=failed；testOperationId 尚为空，没有成功测试部署或正式晋级证据。
- zeroWriteEvidence=false、retryable=true。后者仅是工作流字段，不能直接当作安全重试许可；前者说明不能声称已经证明完全零远端写入。

## 做对的部分
1. 使用新隔离 worktree 和批准提交，未看到把旧失败包/r105/r106 拼接成新发布成功。
2. 页面自动化脚本从 READY workflow 行定位“部署测试服”按钮，等待对应 publish-test POST，且断言只发生一次该写请求；不是直接绕过页面调用发布脚本。
3. 源和 digest 在构建/部署间保持绑定；没有把 READY 当作已部署成功。
4. 锁失败后最后可见行动为只读核对，明确不手工清锁、不重复点击、不继续正式服写入；最后轮次已中断，不能声称仍有发布进程在有效运行。

## P1：锁获取 SQL 的赋值顺序风险与当前自锁症状吻合

精确文件：D:/IntRuoyiWorktree/r260924-r22-button-release-r2/maintenance/ops/deploy/publish-int-ruoyi.ps1。

- 5864 行的 Invoke-ReleaseOperationLockAcquire 使用 INSERT ... ON DUPLICATE KEY UPDATE。
- 5878–5882 行在旧状态不是 RUNNING 时更新 operation_id/release_tag/started_at 等。
- 5883 行随后把 status 改成 RUNNING。
- 5884–5889 行却继续用 `IF(status = 'RUNNING', 旧值, 新值)` 决定 executor、lease_token、heartbeat 和 write_fence。
- 若更新分支中的后续表达式读取到已修改 status，新 operation/tag 会写入，而旧 lease/executor/fence 继续保留。5893 行的所有权确认要求新 lease，因此返回 LOCK_HELD，即使显示 owner operation/tag 已是自己。

本次实际日志确实为 `LOCK_HELD:test-release-20260923-175920-9e66dcb4e9e6-app:...`，即与本次 tag 相符。该症状应优先检查“旧终态锁行复用后租约未更新”，而不是默认归因另一个任务。

MySQL 官方文档说明 UPDATE 读取当前列值，单表赋值通常按从左到右计算，ON DUPLICATE KEY UPDATE 在唯一键冲突时更新旧行：
- [UPDATE 赋值规则](https://dev.mysql.com/doc/refman/8.0/en/update.html)
- [INSERT ... ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.0/en/insert-on-duplicate.html)

这是由源码和 SQL 语义推导的高优先级缺陷假设，与现场错误一致；本审查未读取远端原锁行的旧状态/真实 lease，也未运行真实 MySQL 复现，所以不宣称已经最终证明本次现场根因。

现有测试缺口：scripts/tests/test_release_operation_lock_mysql_behavior.py:193 的 reacquire 测试在 216–228 行手写 UPDATE 直接设置新 owner/lease/fence，没有执行生产中的这条 INSERT ... ON DUPLICATE KEY UPDATE。它能证明旧 owner 被拒绝，不能覆盖当前获取锁 SQL 的顺序问题。

建议在独立真实 MySQL 测试中直接运行生产命令生成结果，覆盖：无锁首次获取、旧 FAILED/APPLIED 行重新获取、同 tag 不同进程/lease、他人 RUNNING 锁拒绝、失权后零业务写入。先复现再修复；若修改批准提交之外的发布器，必须按当前精确 GO 的边界重新提交独立复检，不能就地修改冻结发布器或仅重设 SHA。

## P1：任务日志包含明文登录凭据

目标 execution-log.md 第 584、597 行直接复述了包含口令的用户指令，同文件又声称记录不含口令，存在事实矛盾。本报告仅记录位置，不复制凭据。

建议立即脱敏目标文档及相关输出，核对是否已暂存/提交/共享；仅保留用户允许的身份、范围及授权证据。用户在聊天中提供口令不授权将口令落入仓库文档。本审查不修改目标任务文件，也不将该文件纳入审查提交。

## P2：机器状态仍写“未部署”，与真实失败不一致

`doc/tasks/20260919-button-only-prod-release/task-state.json` 的 r22ButtonRelease.testDeploymentStarted 仍 false，releaseOperations 对当前 tag 仍写 BUILT_READY...TEST_NOT_DEPLOYED，phase 仍为 READY/admin preflight；真实 workflow 已 TEST_DEPLOYING 失败，operation 存在且 failed。

必须记录“按钮已提交、部署失败、锁归属待核对”，不能继续按未点击/纯 READY 推动下一次部署。历史 READY 包及摘要仍可作为构建证据，但不能覆盖新的失败态。

## 当前下一步
1. 固定 d9764032 operation、workflow FAILED 及相关日志，更新任务机器状态，先脱敏明文凭据。
2. 只读核对远端锁 operation/tag、executor host/PID/identity、heartbeat、lease 和 fence，并与本次执行器对应；真实 token 不输出或提交。
3. 并行独立复现旧终态锁行的真实获取 SQL，确认是否为赋值顺序问题；不得先手工改锁/清锁再重试。
4. 若必须改发布器，完成 BDD/TDD、两端合同和独立复检；新代码不能沿用旧精确提交 GO。若只是已证明的孤儿锁，走现有受控恢复入口及所有权门禁，不直接改表。
5. 测试服运行态、版本和真实页面验收通过后，才可对同一合格发布包 mark-tested/promote-prod；当前不能开始正式晋级。

## 审查验证与边界
已核对精确任务记录、批准提交、当前 clean worktrees、workflow/operation 文件、发布日志、按钮脚本和锁 SQL/测试。未运行 CI、构建、产品测试或真实 SQL；未连接服务器、修改目标任务或发送外部消息。本次结论为当前证据快照，不等于目标任务成功或代码已修复。
