# 执行日志
## 2026-07-08T08:13:59+08:00
- USER: 构建发布到测试服务器。
- BDD: code-only 测试服发布 -> Given 三仓目标提交已固定且主工作区存在不相关未提交内容 / When 在专用干净临时发布 worktree 执行 build-release 与 publish-test / Then 发布包 manifest 必须 dirty=false，测试服必须运行同一 releaseTag。
- GREEN: previous-task-status-check -> PASS，20260707-showroom-legacy-order-prod-release 最终状态为已完成；已校正 Current Status 为 completed。
- GREEN: experience-preflight -> PASS，已读取 docs/experience-index.md、docs/release-agent-checklist.md、docs/release-build-preflight-lessons.md、docs/powershell-preflight-lessons.md、D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md、D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md、D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md 与 CI/CD 技能门禁；本次只执行测试服发布，不触碰正式服/备份服/备份/恢复/回滚。
## 2026-07-08T08:15:39+08:00
- GREEN: release-worktree-create-verify -> PASS，短路径临时发布 worktree 已验证：D:\ProjectPackage\Int\IntRuoyiWorktrees\r260708test；维护仓/后端/前端均为计划提交且 dirty=false。
## 2026-07-08T08:16:54+08:00
- GREEN: runtime-control-config-switch -> PASS，已备份 $backup，并将 repo-root/frontend-root 切到 $base\b 与 $base\f。
## 2026-07-08T08:18:27+08:00
- GREEN: runtime-control-restart-and-build-preview -> PASS，本机 48181 已重启并重新加载临时 worktree 配置；build-release 预览指向 r260708test/b 与 r260708test/f，包含 SkipDatabaseSync/SkipMinioSync，未出现正式服/备份/回滚/恢复动作。
## 2026-07-08T08:18:49+08:00
- GREEN: runtime-control-preview-recheck -> PASS，本机 48181 health=UP；build-release 预览指向 r260708test/b 与 r260708test/f，包含 SkipDatabaseSync/SkipMinioSync，未出现正式服/备份/回滚/恢复动作。
## 2026-07-08T08:22:22+08:00
- GREEN: build-preflight-gates -> PASS，migration policy gate、前端 pnpm install --frozen-lockfile、后端 yudao-server 目标模块构建门禁均通过。
## 2026-07-08T08:22:47+08:00
- GREEN: build-release-submit -> PASS，operationId=op-2026-07-08T002247940620100Z-0f904898-a2ab-49c8-a8b5-3c8351191d78，已通过运行控制台触发 code-only build-release。
## 2026-07-08T08:35:17+08:00
- GREEN: build-release -> PASS，releaseTag=20260708_082248，operationId=op-2026-07-08T002247940620100Z-0f904898-a2ab-49c8-a8b5-3c8351191d78，manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\20260708_082248\manifest.json；publishScope=code-only；backend commit aa62aaef666be5d7f0fd1c2dc9a2ffb1357aedf0 dirty=false；frontend commit 4e72522b16fadd2d2c54b138ab5a25e12b7146e7 dirty=false；未包含数据库/MinIO/运行数据目录。
## 2026-07-08T08:35:36+08:00
- GREEN: publish-test-preview -> PASS，releaseTag=20260708_082248，预览包含 -Environment test、ServerHost=172.30.30.58、RemoteAppDir=/opt/intruoyi/runtime，未出现正式服/备份/回滚/恢复动作。
## 2026-07-08T08:36:23+08:00
- GREEN: publish-test-submit -> PASS，releaseTag=20260708_082248，operationId=op-2026-07-08T003601417252800Z-cec73968-b79f-44fc-ae57-b6c765d9e182，已通过运行控制台触发测试服部署。
## 2026-07-08T08:49:05+08:00
- GREEN: publish-test -> PASS，releaseTag=20260708_082248，operationId=op-2026-07-08T003601417252800Z-cec73968-b79f-44fc-ae57-b6c765d9e182，测试服部署 operation=SUCCESS。
## 2026-07-08T08:49:30+08:00
- GREEN: test-server-runtime-verification -> PASS，releaseTag=20260708_082248，测试服 .env IMAGE_TAG、backend/frontend 容器镜像 tag、backend health=UP、frontend HTTP 200 均通过。
## 2026-07-08T08:50:05+08:00
- GREEN: runtime-control-main-restore -> PASS，已从 D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.before-20260708-test-release.yaml 恢复 config/runtime-control.local.yaml，重启 48181 后 health=UP，预览不再指向 r260708test。
## 2026-07-08T08:51:21+08:00
- GREEN: release-worktree-cleanup -> PASS，本次临时发布 worktree D:\ProjectPackage\Int\IntRuoyiWorktrees\r260708test 已删除，三仓 worktree metadata 已 prune。
## 2026-07-08T08:51:52+08:00
- GREEN: final-runtime-and-cleanup-verification -> PASS，runtime-control 已恢复主路径且 health=UP；r260708test 临时 worktree 已删除；测试服 releaseTag=20260708_082248 运行态复核通过；临时配置备份已删除。
