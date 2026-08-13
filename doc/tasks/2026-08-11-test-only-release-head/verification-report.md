# Verification Report

## Scope

仅测试服发布验证，范围为发布开始时当前分支 HEAD 的已提交代码。

## Results

- Source isolation: PASS。最终发布维护仓 HEAD=`97723ac524487595ab5b145e31251d6bc1ec0091`，主程序 HEAD=`5d503ea5e5d754461031ddb4271e5db77c2c4d91`；两个 r260812b 专用 release worktree 均 clean，主工作区未提交改动未进入构建输入。
- Release prerequisite toolchain: PASS。Java/Maven/Node/pnpm/Docker/SSH/Git/Python 可用，隔离控制台候选端口无监听。
- Test server pre-release baseline: PASS（只读）。当前仍运行上一成功版本 `release-20260811-intmain-head-test-r260811a-r2`，backend/frontend running、health=`UP`、frontend HTTP=`200`。
- Migration policy contract: REMEDIATED/PASS。维护仓正式修复已完成严格 RED/GREEN：policy gate 接受并审计 evidence-only 类型，PowerShell required SQL 只收集 executable 类型，并增加 executable 不得依赖 evidence-only 的闭包门禁；冻结 app SQL 全量扫描 `status=passed`、`migrationCount=474`。修复仍需完成维护构建、提交、合回 `int_main` 后才能作为新发布输入。
- Maintenance console build: PASS。固定 Corepack 10.25 与外部 build policy 后 `ignored-builds=None`、`pendingBuilds=[]`；前端 typecheck/build 与 Maven 26 tests/package 全部通过，jar SHA256=`3eae95d8b68f802509a29d66e85e06b1dd54074d49b95b9686826a2b13341e58`，包含静态页面。
- Release package / manifest / version / changelog: PASS。releaseTag=`release-20260813-intmain-head-test-r260812b-r2`，build operation=`op-2026-08-12T190406618402500Z-3771efa2-38a7-4bf1-be8e-3e0f1f237bde` SUCCESS；484 个 artifact hash/size、sourceRepos commit/dirty=false、manifest 与前端 image release-info/changeSet 一致。
- Publish-test: PASS。operation=`op-2026-08-13T001732036464300Z-1541e376-2561-40b8-82c8-77c33bcfda17` SUCCESS；范围仅 test，未执行 mark-tested/promote-prod/promote-backup，正式服和备份服未操作。
- Runtime: PASS。测试服 `.env IMAGE_TAG` 和 backend/frontend 实际镜像均为目标 tag；两个容器 running；backend Actuator HTTP 200/UP；frontend HTTP 200；release-info source commit/dirty、lock=APPLIED；migration total=430/APPLIED=4/SKIPPED=426/FAILED-RUNNING=0；活跃上传槽重复组=0。
- Page verification: PASS。Playwright 真实打开测试前端登录页，关键接口 200、console errors=0；运行控制台显示目标 releaseTag，点击“查看变更”后版本号、发布包和组件范围均一致，六个控制台 API 200、console errors=0。
- Problems and experience: PASS。Git/worktree、migration contract、pnpm、NAS config/releaseTag、发布数据、日志脱敏、长 operation、远端探针与页面加载问题均按现象/阶段/影响/原因/动作/结果/前置检查/自动化/避免方式记录，并合并到既有发布前置经验与索引。
- Closeout: PASS。五个任务 worktree、两个 state 根和任务分支均已清理；Git 注册/物理路径无残留。48181 由主维护路径 PID=5600 提供，health=UP、testCurrentReleaseTag=r2、prod/backup access disabled；清理后远端全量 postcheck 再次 PASS。

## Final Conclusion

PASS / COMPLETED。构建、仅测试服发布、真实运行态、页面、经验沉淀、稳定控制台恢复、worktree/state 清理和清理后远端复核全部通过；task-closeout preview/apply 无阻塞、无警告，仅保留三份正式任务记录，任务已完成。
