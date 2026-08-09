# 2026-08-09 当前 HEAD 仅测试服发布验证报告

## Conclusion

PASS。发布包只来自任务启动时冻结的已提交 HEAD；同一 releaseTag 的 `build-release -> publish-test` 均成功；测试服真实运行态、前端页面和运行控制台版本变更说明全部通过。未执行正式服、备份服、`mark-tested`、`promote-prod` 或 `promote-backup`。

## Frozen Source

- 维护仓 `int_main`：`1978562394fbc722f8b534988ddf1e3f0e4f8846`。
- 主程序仓 `int_main`：`199836c5fc105033898c2df59fb8ca22ac005625`。
- 维护构建 worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260809a\m`，detached、clean。
- 主程序构建 worktree：`D:\IntRuoyiWorktree\r260809a-release-app`，detached、clean。
- 两个主工作区均存在大量未提交改动，因此未作为构建输入；构建后两个 release worktree 复核 clean。

## Build And Manifest

- releaseTag：`release-20260809-intmain-head-test-r260809a-r1`。
- 维护控制台：前端 typecheck/build PASS；Maven tests 26 passed；JAR SHA256=`054c79ff442ccad4b5fbfd8f55958131b5b7ebdbbf0650098511bf52065ebfd3`。
- build operation：`op-2026-08-09T154417143232100Z-1cbd9f9c-35e8-4b3f-9cda-1646af3f808f`，SUCCESS。
- 发布包：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260809-intmain-head-test-r260809a-r1`。
- manifest：467 个 artifact，missing=0、hash mismatch=0；backend/frontend source commit 均为冻结主程序 HEAD，dirty=false；releaseTag、component、publishScope、release-info、changeSet 全部一致。

## Test Server

- publish operation：`op-2026-08-09T155709667969700Z-6d3f54cc-4892-4b0e-8c49-624bacd79bfe`，SUCCESS。
- `.env IMAGE_TAG`、backend image、frontend image：均为本轮 releaseTag。
- backend/frontend 容器：running。
- backend health：HTTP 检查退出码 0，body status=`UP`。
- frontend：HTTP 200，HTML 标题=`瑛泰管理系统`。
- release-info：releaseTag、source commit、dirty=false、变更说明均一致。
- release lock：`test:<releaseTag>:APPLIED`。
- migrations：APPLIED=8、SKIPPED_ALREADY_APPLIED=411、FAILED/RUNNING=0。

## Browser Verification

- 测试服页面：Playwright HTTP 200，进入真实登录页，标题=`瑛泰管理系统 - 登录`，console error=0，failed request=0。
- 运行控制台：Playwright HTTP 200，点击 `查看变更` 后可见本轮 releaseTag、发布包和 `组件范围：intruoyi`；build/publish 两条 operation 均为 SUCCESS，console error=0，failed request=0。

## Closeout

- PID 26248 的任务控制台已停止，48182 无监听；`r260809a` 两个 release worktree/state 的 Git 注册、物理路径和进程引用清理通过；无新提交、无需合回 `int_main`。
- 清理后的最终测试服远端复核再次 PASS。
- task-closeout preview/apply 均 PASS，blocked/warnings=`none`；一次性 evidence/helper 与 Playwright 临时截图已删除，只保留三份正式任务记录。
- 最终状态：`completed`。
