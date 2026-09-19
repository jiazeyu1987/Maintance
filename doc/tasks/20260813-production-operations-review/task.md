# 正式服日常运维模式评估

## Task Goal

基于当前 IntRuoyi 维护仓、主程序运维文档、发布脚本、备份恢复机制和已有运行证据，评估正式服务器平常应采用的软件更新、备份恢复、运行监控和数据分析模式；本任务只做本地只读审查，不连接或修改正式服务器、数据库及远端环境。

## Milestones

- [completed] M1：核对当前发布、备份恢复、服务器访问和运行控制机制。
- [completed] M2：盘点监控、容量、数据分析和安全运营的现状与缺口。
- [completed] M3：形成按日/周/月/季度执行的正式服运维建议和优先级。
- [completed] M4：完成证据记录、只读验证和任务收尾。

## Expected Verification

- 每项建议均能追溯到现有文档、脚本或明确标注的现状缺口。
- 不把“存在备份”误判为“可恢复”，恢复就绪结论必须以演练证据为准。
- 不虚构流量、SLO、RTO/RPO、告警平台或成本数据；未知项明确列为待决策门禁。
- 不连接正式服务器，不执行构建、测试、发布、备份、恢复、重启或数据写入。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；从发布可追溯、恢复可验证、运行可观测、数据可治理四个持续机制设计运维模型。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- 发布、备份、恢复和服务器容量先以 `E:\IntRuoyi\docs\release-backup-restore.md` 为准；正式环境访问以 `E:\IntRuoyi\docs\server-access.md` 为准。
- 完整发布只认同一 `releaseTag` 的 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup` 闭环，且发布输入必须来自本次专用 clean release worktree 的已提交内容。
- 正式发布成功必须同时核对 operation、manifest、远端 `.env IMAGE_TAG`、前后端镜像 tag、后端 health 和前端 HTTP 200；证据不完整不得判定成功。
- 备份就绪必须包含可验证的恢复演练；备份文件存在、任务成功或副本数量都不能单独证明可恢复。
- `/mnt/nas` 是公司共享盘，禁止删除、清空、移除挂载或修改 fstab；本任务不触碰该资源。
- 没有业务目标与实测证据时，不虚构 RTO/RPO、SLO、容量阈值、流量和成本结论。
- 命令和记录必须脱敏，不记录密码、token、私钥、连接串或秘密环境变量。

## Current Status

completed

## Final Verification

- UTF-8 无 BOM 复读通过；`git diff --check` 通过，仅有仓库既有 LF/CRLF 提示。
- `task-closeout-cleanup` preview/apply 均通过，保留三份核心任务记录，无删除项、阻塞或警告。
- 本任务未连接远端服务器，未执行构建、测试、发布、备份、恢复、重启或数据写入。
