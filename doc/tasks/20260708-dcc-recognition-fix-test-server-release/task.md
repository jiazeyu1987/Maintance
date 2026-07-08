# 20260708 DCC 识别修复发布测试服

## 任务目标

将 IntRuoyi 后端已验证的 DCC 产品名称/基础信息识别非 Codex 修复发布到测试服务器，并用测试服真实运行态确认非 Codex 阻塞清零。

## 里程碑

- [x] M1 创建干净发布 worktree，固定后端修复提交与前端发布提交。
- [x] M2 将维护控制台发布配置切到临时发布 worktree并重启验证。
- [x] M3 通过 code-only build-release 构建发布包，确认发布包可用。
- [x] M4 部署测试服并确认后端与前端镜像均为 fix-4。
- [x] M5 测试服真实运行态审计：active claim=0、running task=0；未发现本次 fix-4 发布完成后的新增识别任务报错。
- [x] M6 记录当前阻塞已解除；临时 worktree/config 清理另按收尾预览执行，不混入本次提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，修复识别状态长度/恢复清理逻辑，并修正测试服发布模板端口契约。
- 是否存在临时补丁或绕过：否；本次未手工改写 DCC 业务数据，未把历史失败记录伪装为成功。

## 预期验证

- 发布包 `release-20260708-dcc-recognition-fix-4` 可用，publishScope=`code-only`，component=`intruoyi`，checksumPresent=true。
- 测试服后端健康检查 HTTP 200，响应 `{"status":"UP"}`。
- 测试服前端 HTTP 200，后端与前端容器镜像均为 `release-20260708-dcc-recognition-fix-4`。
- 测试服数据库审计 active claim=0、running task=0。
- 测试服失败分组中最新 `DATA_TOO_LONG` 记录为 `2026-07-08 08:47:11`，早于本次发布完成时间 `2026-07-08 16:41:35`，未发现发布完成后的新增非 Codex 失败。

## 当前状态

- completed

## 最终验证结果

- `publish-test` operation `op-2026-07-08T082438118967200Z-e7f5a609-a1a6-4f19-bd0b-539c714543b2` 最终 `SUCCESS`。
- 测试服发布锁 `test-release-20260708-dcc-recognition-fix-4` 已从 `RUNNING` 正常释放为 `APPLIED`，finished_at=`2026-07-08 16:41:35`。
- 远端 `.env` 为 `IMAGE_TAG=release-20260708-dcc-recognition-fix-4`、`BACKEND_HOST_PORT=48081`、`FRONTEND_HOST_PORT=8081`。
- `intruoyi-backend` 与 `intruoyi-frontend` 均运行 `release-20260708-dcc-recognition-fix-4`。
- DCC 识别真实表审计：`dcc_controlled_file_recognition_claim` active_claims=0；`dcc_controlled_file_batch_recognition_task` running_tasks=0。
