# 20260703 build-publish-test-again

## 任务目标

- 再次构建并发布到测试服务器。
- 默认沿用上次发布口径：测试服 code-only / 不带数据，不执行 mark-tested、正式服、备份服、备份、恢复或回滚。

## 经验门禁

- 适用索引：`docs/experience-index.md`
- 强制门禁：
  - 发布前必须读取 `docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。
  - 必须新建本次专用临时发布 worktree，构建输入只允许来自目标提交的已提交内容。
  - code-only / 不带数据发布仍必须检查 manifest、required SQL、migration、schema/约束门禁和发布包无数据目录。
  - 发布成功判定必须同时核 operation=SUCCESS、manifest、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200。
  - 临时发布 worktree 指向 runtime-control 后，收尾前必须恢复主路径并验证健康检查。

## 里程碑

- [x] 创建任务目录并记录目标。
- [x] 完成经验、服务器、备份恢复、worktree 发布门禁预检。
- [x] 创建本次专用临时发布 worktree 并确认目标提交。
- [x] 构建 code-only 发布包并校验 manifest。
- [x] 发布到测试服务器并校验运行态。
- [x] 恢复配置、清理临时 worktree、记录结论并提交任务记录。

## 预期验证

- build-release operation SUCCESS。
- publish-test operation SUCCESS。
- manifest `publishScope=code-only` 且 sourceRepos commit/dirty 正确。
- 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 均等于本轮 releaseTag。
- backend health=UP，frontend HTTP 200。
- 临时发布 worktree 已按规则清理或阻塞记录。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，沿用临时发布 worktree 与 manifest/运行态完整校验。
- 是否存在临时补丁或绕过：否。

## 当前状态

- 状态：已完成。
- 结论：已构建并发布到测试服务器，releaseTag=release-20260703-0912-test-again。
- build-release operation=op-2026-07-03T011522088783Z-a5911d73-7521-4ff2-a583-32d202173206，状态 SUCCESS。
- publish-test 首次 operation=op-2026-07-03T080000300286800Z-15fd0acf-70e5-483a-8585-82bc282ce473 因误启用 Smart Release report-only 且缺少测试服 target config 失败，已记录并按本次 code-only 发布口径关闭可选报告重试。
- publish-test 重试 operation=op-2026-07-03T080239101028700Z-e0b55e76-a62e-4445-be42-248ed979a170，状态 SUCCESS。
- 最终验证：manifest publishScope=code-only，sourceRepos dirty=false；测试服 .env IMAGE_TAG、backend/frontend 实际镜像 tag 均为本轮 releaseTag；backend health=UP；frontend HTTP 200；pdf worker HTTP 200。
- 临时发布 worktree 已清理，runtime-control.local.yaml 已恢复主路径并验证 health=UP。
- 边界：本轮未执行 mark-tested、正式服、备份服、备份、恢复或回滚。
