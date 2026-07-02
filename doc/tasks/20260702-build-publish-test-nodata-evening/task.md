# 20260702-build-publish-test-nodata-evening

## 任务目标

构建并发布当前已提交代码到测试服务器，不带数据同步。

## 里程碑

- [x] 创建任务记录与经验门禁
- [x] 核对发布入口、目标提交和 no-data 参数
- [x] 创建/确认隔离发布 worktree
- [x] 构建 code-only 发布包
- [x] 发布到测试服务器并验证运行态
- [x] 收尾清理、记录证据并提交本任务变更

## 预期验证

- build-release operation=SUCCESS，且 manifest 存在。
- manifest 的 sourceRepos 对应本轮计划提交，dirty=false。
- 发布范围为 code-only / 不带数据，构建参数包含 SkipDatabaseSync 与 SkipMinioSync。
- publish-test operation=SUCCESS。
- 测试服 172.30.30.58 远端 .env IMAGE_TAG、backend/frontend 镜像 tag 与本次 releaseTag 一致。
- 后端 /actuator/health 返回 UP，前端 HTTP 200。

## 当前状态

COMPLETED：2026-07-03 01:07:42 +08:00

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## 经验门禁

- PowerShell：不使用 &&；中文读写和命令输出显式 UTF-8。
- 发布输入：每次发布使用本次专用临时发布 worktree；构建输入只允许 Git 已提交内容，未提交/未跟踪内容不得进入发布包。
- 发布范围：本任务为不带数据发布，build-release 必须包含 -SkipDatabaseSync 与 -SkipMinioSync，不执行数据库整库同步、MinIO 同步、备份、恢复或回滚。
- 测试服目标：publish-test 仅允许 Environment=test、ServerHost=172.30.30.58、RemoteAppDir=/opt/intruoyi/runtime。
- 发布完成判定：必须同时核 operation=SUCCESS、manifest、远端 .env IMAGE_TAG、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200。

## 本轮计划提交

- maintenance：int_main / efcd45f03d5b281af7b6a3174220cb635cf373ae
- backend：int_main / f87b8485ea992674727ee7b32b96ca07a365e70b
- frontend：int_main / 4decbf980d55f01ab64ca6c46b79fe62d9ab3071

## 工作区状态记录

- maintenance dirty：true
- backend dirty：false
- frontend dirty：false
## 本轮发布 worktree

- backend：D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260702-2151-nodata-evening / f87b8485ea992674727ee7b32b96ca07a365e70b
- frontend：D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2151-nodata-evening / 4decbf980d55f01ab64ca6c46b79fe62d9ab3071
- 配置备份：config/runtime-control.local.before-nodata-evening-20260702-2151.yaml

### DCC 已删除历史分类生命周期迁移修复
- 状态：已完成本地 RED/GREEN。
- 根因：测试库存在 147 条 deleted=1 历史分类归档行，活动行已补齐，但 NOT NULL 变更覆盖全表，导致发布迁移在 ALTER TABLE dcc_file_category MODIFY lifecycle_stage NOT NULL 阶段失败。
- 处理：已删除历史分类行在 NOT NULL 前归一化为 TRANSFER，并新增全表非空门禁，避免 MySQL 泛化错误。
- 验证：Python 契约测试、DCC Java schema 测试、发布迁移策略门禁均通过。
### 无数据发布 fix3 worktree
- releaseTag：release-20260703-0009-nodata-evening-fix3
- 后端 worktree：D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260703-0009-nodata-evening-fix3
- 后端目标提交：8b9b0bd7450413202423b1a61aea5530f14a6436
- 前端 worktree：D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260703-0009-nodata-evening-fix3
- 前端目标提交：4a89359a739ba69f5d1ce348e324455968fb28cb
- 状态：已创建并验证 clean。
## 完成记录
- 状态：COMPLETED
- 完成时间：2026-07-03 00:58:21 +08:00
- 最终 releaseTag：release-20260703-0009-nodata-evening-fix3
- build-release operation：op-2026-07-02T161541001144800Z-e41fd403-d2ff-4b9c-83a7-fc1f4225577d，结果 SUCCESS。
- publish-test operation：op-2026-07-02T163956246337200Z-32587742-51dc-4f73-9f5a-8b84ce3e2d9e，结果 SUCCESS。
- 发布范围：code-only / 不带数据；构建包 publishScope=code-only，发布目录无 database/db-dump/mysql-dump/minio/files/runtime-data/data/docker-build-context。
- 发布输入：backend commit 8b9b0bd7450413202423b1a61aea5530f14a6436，frontend commit 4a89359a739ba69f5d1ce348e324455968fb28cb，manifest dirty=false。
- 测试服运行态：.env IMAGE_TAG、backend/frontend 镜像 tag 均为 release-20260703-0009-nodata-evening-fix3；backend health=UP；frontend HTTP 200；pdf.worker.mjs HTTP 200 application/javascript。
- 迁移核验：dcc_file_category.lifecycle_stage 空值数为 0，列已为 NOT NULL varchar(32)。
- 后续边界：未执行 mark-tested、正式服、备份服、备份、恢复或回滚。