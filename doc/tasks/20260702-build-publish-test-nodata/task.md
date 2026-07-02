# 20260702-build-publish-test-nodata

## 任务目标

成功构建并发布到测试服务器，不带数据。

## 里程碑

- [x] 任务前置检查与经验门禁
- [x] 创建不带数据发布包
- [x] 发布到测试服务器
- [x] 验证测试服务器 operation=SUCCESS、manifest、远端 IMAGE_TAG、镜像 tag、后端 health=UP、前端 HTTP 200
- [x] 完成任务记录与提交

## 预期验证

- build-release 不带数据成功：PASS，operation=op-2026-07-01T235523602125100Z-ce23456f-d0f7-415a-a575-2e1ca7228f23
- publish-test 成功：PASS，operation=op-2026-07-02T001015631437900Z-571f3f40-9ade-41b1-b681-13abd4c035b6
- 测试服务器后端健康检查 UP：PASS
- 测试服务器前端 HTTP 200：PASS

## 当前状态

COMPLETED：2026-07-02 08:23:55 +08:00

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## 经验门禁

- PowerShell：不使用 &&；中文读写和命令输出显式 UTF-8。
- 构建发布：必须使用本次专用 releaseTag；构建产物必须校验 manifest；失败/中断的旧 releaseTag 不得继续发布。
- no-data 范围：构建预览/命令必须包含 -SkipDatabaseSync 与 -SkipMinioSync，发布验证不做数据/对象同步验收。
- 测试服目标：仅允许发布到 172.30.30.58，远端目录 /opt/intruoyi/runtime；不得触发正式服、备份服、恢复或回滚动作。
- 完成判定：operation=SUCCESS、manifest 存在、远端 .env IMAGE_TAG=<releaseTag>、后端/前端镜像 tag 一致、后端 health=UP、前端 HTTP 200。

## 发布结果

- releaseTag：release-20260702-0738-codeonly-test
- build-release operation：op-2026-07-01T235523602125100Z-ce23456f-d0f7-415a-a575-2e1ca7228f23
- publish-test operation：op-2026-07-02T001015631437900Z-571f3f40-9ade-41b1-b681-13abd4c035b6
- 发布范围：code-only / 不带数据
- 测试服：172.30.30.58
- 后端健康：UP
- 前端 HTTP：200
- PDF worker HTTP：200

## 最终验证结果

PASS：测试服 .env IMAGE_TAG、后端镜像、前端镜像均为 release-20260702-0738-codeonly-test；后端 /actuator/health 返回 UP，前端 http://172.30.30.58:8081/ 返回 HTTP 200。
