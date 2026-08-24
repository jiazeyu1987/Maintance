# Verification Report

## Scope

本报告覆盖修复提交后的单一 r11 releaseTag：从专用 clean release worktree 构建维护控制台和测试发布包，仅发布测试服务器 172.30.30.58；不包含正式服、备份服、mark-tested 或 promotion。

## Results

- Source isolation: PASS。maintenance worktree 为 2307b93c2ce541b7458c4e7c524810d0b1f6687f，app worktree 为 4f1f847b63bd82bb53ffc0081d7eeecfb1f5c47f；两者构建前后 clean。主工作区 dirty 改动未进入构建。
- Fix and regression: PASS。生产角色 required SQL 临时表重复打开修复提交 4f1f847b63bd82bb53ffc0081d7eeecfb1f5c47f；迁移合同 10 passed，迁移策略 gate 17 passed。
- Build: PASS。releaseTag=release-20260823-intmain-training-r260823f-r11；build operation=op-2026-08-24T115227267149700Z-05373329-a53c-4c18-902b-428b115ecb68 SUCCESS；Maven backend BUILD SUCCESS、frontend pnpm build:test、Docker package 均成功。
- Package/manifest: PASS。package=E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260823-intmain-training-r260823f-r11；manifest validator MANIFEST_VALIDATION_PASSED；manifest.json/release-manifest.json 的 releaseTag、sourceRepos commits、dirty=false、publishScope=code-only、changeSet.summary 与本次提交一致。
- Publish-test: PASS。preview gate PASS；publish operation=op-2026-08-24T130555285358Z-d4c042ba-6f92-4f8e-a4d1-a380601bca5f SUCCESS；target=test；未执行 mark-tested、promote-prod、promote-backup。
- Runtime: PASS。测试服 .env IMAGE_TAG 和 backend/frontend 实际镜像均为 r11；容器 running；backend Actuator HTTP 200/status UP；frontend HTTP 200；release-info HTTP 200 且 sourceRepos/dirty/changeSet 与 manifest 一致；目标 release lock 最新状态 APPLIED；RUNNING lock=0；目标 migration FAILED/RUNNING=0。
- Frontend page: PASS for public entry. Playwright 真实打开 http://172.30.30.58:8081/，页面标题为“瑛泰管理系统 - 登录”，登录相关 HTTP/API 请求为 200，console errors=0。认证后业务页未继续：测试服预填 admin 密码已过期，tenant selector 无数据；此缺口作为 ISSUE-016 记录，未猜测凭据、改账号或 API 绕过。
- Runtime console: PASS。Playwright 打开 http://127.0.0.1:48181/，操作记录显示 publish operation SUCCESS；测试服显示 r11；版本变更说明显示发布包、组件范围 intruoyi 和提交 4f1f847b63bd 的变更摘要；正式服和备份服均未上报；console errors=0。
- Problems and experience: PASS。ISSUE-001..016 已在 execution-log.md 记录；r10 中断 RUNNING、旧控制台 preview、MySQL ERROR 1267/1137、SSH carrier warning、数据库 lock operation_id 契约和认证基线过期已沉淀到既有发布、worktree、登录经验文档及索引。
- Closeout status: COMPLETED。task-closeout preview/apply 通过；本任务 r11 release worktree 物理目录与 Git 注册均已清理；任务控制台进程已停止并恢复到维护仓稳定 JAR，48181 `/actuator/health` 返回 HTTP 200。

## Final Conclusion

PASS / COMPLETED。构建来源、发布包、仅测试服发布、测试服真实运行态、前端入口和运行控制台版本/变更说明均已通过；认证后业务页因测试服登录基线过期保留为已知问题，不影响本次代码发布静态入口和运行控制台验收，但下次发布前必须前置检查。
