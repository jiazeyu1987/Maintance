# 发布安装包与测试/正式服脚本审查

## Task Goal

检查当前构建、测试服发布、正式服发布脚本及其契约，评估是否能形成“同一安装包可依次发布到测试服和正式服”的稳定流程，并向非代码用户给出可执行建议。本任务只读审查，不执行构建、发布或远程操作。

## Milestones

- [completed] M1：读取适用经验、发布规范和现有脚本，建立当前链路清单。
- [completed] M2：审查安装包的完整性、环境无关性、校验、迁移、回滚与审计能力。
- [completed] M3：形成按优先级排序的优化建议和目标流程。
- [completed] M4：记录验证证据；任务进入收尾检查。

## Expected Verification

- 现有构建、测试服发布、正式服发布入口均已识别。
- 建议逐项对应到具体脚本或缺失契约。
- 明确同一 releaseTag、不可变安装包、环境配置外置、发布前检查、发布后验证和回滚要求。
- 不执行构建、测试、发布、服务器写入或远程环境变更。

## 经验门禁

- Trigger：审查构建/发布/回滚链路。
- Preflight check：读取 `docs/experience-index.md` 命中的发布经验、`E:/IntRuoyi/docs/release-backup-restore.md`；仅审查已提交脚本与文档。
- Blocker：发布契约、脚本入口或所需文档缺失时，明确记录缺口，不用推测或 fallback 填补。
- Verification：核对单一 `releaseTag` 从 build-release 到 test/prod/backup 的证据链，以及 operation、manifest、镜像 tag、health、HTTP 状态要求。
- Forbidden action：未经用户授权不得构建、发布、登录服务器、改动远程环境或执行回滚。
- Evidence：脚本路径、关键参数/校验点、文档约束和只读检查命令。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；以不可变安装包和统一发布器为目标审查。
- 是否存在临时补丁或绕过：否。

## Current Status

completed

## Completed Work

- 已确认本任务范围为只读审查与建议，不执行任何发布动作。
- 已确认现有链路具备单一 releaseTag 晋级骨架，但尚未达到不可变、强校验、原子入库的单一安装包标准。
- 已形成 4 项 P0、3 项 P1、1 项 P2 建议和三阶段实施顺序。

## Verification Evidence

- 静态读取 `ops/deploy/publish-int-ruoyi.ps1`、`RuntimeControlOperationAction.java`、`RuntimeControlService.java`、manifest validator/schema、发布合同测试和发布规范。
- 关键证据：脚本默认 `Mode=direct`；with-data 路径会重置远端 MySQL；下载包未强制全量哈希复核；tested 门禁只检查文件存在；NAS 使用目录直接复制；OnlyOffice 使用 `latest`；dirty 只记录不阻断。
- 详细证据见 `verification-report.md`。

## Remaining Blockers

- 无审查阻塞。
- 是否实施优化需要用户确认范围；建议先处理 P0，不一次性重写整条发布链。

## Final Verification

- `git diff --check` 对本任务记录、经验索引、发布经验和请求日志通过，仅有仓库既有 LF/CRLF 提示。
- `task-closeout-cleanup` preview/apply 均为 `ready/applied`，保留 task.md、execution-log.md、verification-report.md，无删除项、阻塞或警告。
- 本任务未执行构建、发布、服务器连接、NAS/数据库写入、备份、恢复或重启。
