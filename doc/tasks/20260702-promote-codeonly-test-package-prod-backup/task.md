# 20260702-promote-codeonly-test-package-prod-backup

## 任务目标

将刚才已发布并验证通过的测试服不带数据包发布到正式服务器和备份服务器。

## 发布输入

- releaseTag：release-20260702-0738-codeonly-test
- 构建方式：code-only / 不带数据
- 测试服发布 operation：op-2026-07-02T001015631437900Z-571f3f40-9ade-41b1-b681-13abd4c035b6
- mark-tested operation：op-2026-07-02T003519305152700Z-acc9b02b-d803-4e60-9dd7-74f9f670cca4
- promote-prod operation：op-2026-07-02T003717687464900Z-3af49870-1fdc-4484-be01-19d90747ce36
- promote-backup operation：op-2026-07-02T005123161454400Z-1f1b4219-b991-43da-b37a-8d5e5e14a9b2

## 里程碑

- [x] 任务前置检查与经验门禁
- [x] 核验测试服当前运行包与本次 releaseTag 一致
- [x] 标记测试通过
- [x] 发布正式服务器并验证运行态
- [x] 发布备份服务器并验证运行态
- [x] 完成任务记录、清理预览和提交

## 预期验证

- mark-tested operation=SUCCESS：PASS
- promote-prod operation=SUCCESS：PASS
- promote-backup operation=SUCCESS：PASS
- 正式服与备份服远端 .env IMAGE_TAG=release-20260702-0738-codeonly-test：PASS
- 正式服与备份服 backend/frontend 镜像 tag=release-20260702-0738-codeonly-test：PASS
- 正式服与备份服 backend health=UP，frontend HTTP 200：PASS

## 当前状态

COMPLETED：2026-07-02 09:07:31 +08:00

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## 经验门禁

- PowerShell：不使用 &&；中文读写和命令输出显式 UTF-8。
- 单一 releaseTag：必须复用 release-20260702-0738-codeonly-test，不得重建、换包或拼接其他发布包。
- 正式/备份发布：必须先有测试服成功证据并完成 mark-tested；预览必须包含 ConfirmText=PROD / RequireTested 等门禁参数。
- 正式服目标：只在用户本轮明确授权范围内执行发布与运行态验证，不执行恢复、回滚、备份数据或手工改库。
- 备份服目标：必须使用 172.30.30.59、/mnt/intruoyi-data、/mnt/intruoyi-data/runtime-data、/mnt/intruoyi-data/intruoyi-releases、/dev/mapper/cl-home、intruoyi-minio。
- 完成判定：每个环境均需 operation=SUCCESS、远端 .env IMAGE_TAG、后端/前端镜像 tag、backend health=UP、frontend HTTP 200。

## 发布结果

- 测试服：已运行 release-20260702-0738-codeonly-test
- 正式服：已运行 release-20260702-0738-codeonly-test
- 备份服：已运行 release-20260702-0738-codeonly-test
- 正式服健康：backend UP，frontend HTTP 200，pdf worker HTTP 200
- 备份服健康：backend UP，frontend HTTP 200，pdf worker HTTP 200
- 备份服数据盘：/mnt/intruoyi-data 与 runtime data 均来自 /dev/mapper/cl-home

## 最终验证结果

PASS：同一个 code-only 发布包 release-20260702-0738-codeonly-test 已完成 mark-tested -> promote-prod -> promote-backup，三环境 currentReleaseTag 均一致；正式服和备份服远端 .env、后端/前端镜像 tag、后端健康、前端入口均已核验通过。
