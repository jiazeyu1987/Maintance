# 六步流程重新执行

## Goal
重新执行同步代码、独立构建、测试服发布、正式服发布、正式服增量备份、备份服准备空目标并恢复选定备份链；逐步记录真实耗时。不能用 20261118 已完成结果代替本轮。

## Milestones
- [x] 同步并冻结已提交输入；环境差异及并发归属单独跟进。
- [x] 本轮专用临时 worktree 构建新版本；归档及临时目录清理通过。
- [x] 测试服发布与真实页面验证；基础冒烟 PASS_WITH_OBSERVATIONS。
- [x] 同版本正式服发布与来源恢复验证。
- [x] 修复版本新增量备份与原生成功验证（新点 SUCCEEDED/exit0，worker 已退出）。
- [x] 空目标恢复、数据附件及登录版本验收。
- [x] 耗时汇总与清理本任务 worktree；最终记录独立提交，推送结果以Git回执为准。

## Expected Verification
逐步保存独立 releaseTag、operationId、原生起止时间与客户端单调计时。发布核 manifest/env/实际镜像/健康/HTTP；恢复核选定链、数据、附件字节及真实登录。保留用户批准的历史 PDF 页面元数据限制。仅已提交代码进入构建。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，复用正式流程和计时证据，不新增一次性产品逻辑。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：本轮发布、备份、恢复与真实页面操作。
- Preflight check：核对已完成前序、配置实际路径、远端版本与任务锁、迁移及构建合同、备份链、源恢复和目标保护范围；按阶段阅读 release-backup-restore/server-access/login-access/worktree-memory 及对应 checklist。
- Blocker：活动冲突、提交身份未知、真实合同或依赖不满足；仅阻塞对应步骤。
- Verification：原始操作终态及运行态、真实页面、冻结备份数据；清理后路径及 Git 注册均不存在。
- Forbidden action：不清理正式服 /mnt/nas；不混入未提交修改；不重复派发未知终态操作；不绕过代理/TLS；不使用旧成功证明新运行成功。
- Evidence：本目录 execution-log.md、耗时报告及私密目录原始脱敏回执。

## Current Status
completed（运行、验收、清理已完成；最终记录提交推送回执另核）。

修复提交4a67e8e30、83a856c19已合入并推送int_main，文件71项、PQC34项及完整后端编译通过，修复工作区已清理。固定发布输入83a856c19，版本2026-11-23-08-35-27；测试发布JOB-05b93f6100、正式部署JOB-24a5d2e97e及开放JOB-6888ec0461均成功，实际运行态和真实页面验证通过，非关键外部资源观察项已记录。此前失败构建及旧版本附件页面失败证据保留，不能作为本次成功证据。

新增量smallapp-a535424db6dc4343927dcec7777296f8原生SUCCEEDED/exit0，worker已退出，耗时6792.254786秒；FULL+I1+I2元数据绑定通过，验收基线已冻结。

空目标prepare-94bc75c6-47c6-4ce4-95f7-34c3f00bc118原生INITIALIZED、Spug READY，目标spug-empty59-27cd946a9fc0。整链恢复smallapp-be649e9d7a9e47508ff408c121323c95原生SUCCEEDED/exit0，耗时3387.005434秒；8张表行数、两张图片预览字节、PDF字节、真实登录与版本验收通过。最终只读运行态核对：镜像与manifest一致、health UP、HTTP200、版本一致；恢复worker已退出，PID492确认是serve常驻控制服务，不属于待退出恢复进程。

最终耗时见final-report.md。六个本任务构建/修复路径均已不存在且不在Git worktree登记中；产生的新提交已合入int_main并完成相关验证，稳定控制台路径已核对。本次仅提交本任务记录，推送专用分支codex/sixstep-repeat-20261122-records，不更新远端int_main；专用分支保留当前主线既有祖先历史，不将其他任务工作区改动纳入本次提交。保留历史PDF页面元数据限制和外部统计/头像资源观察项。
