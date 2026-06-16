# 运行控制台原版逻辑对齐

## Task Goal

将当前独立运行控制台改成与原 IntRuoyi 运行控制台业务逻辑一致：补齐原版候选解析、发布包校验、SQL 动作入口、治理接口和前端请求契约；仍保持独立应用本机运行和不接入芋道登录/菜单/角色权限。

## Milestones

- [x] 创建任务目录与 PRD/test-plan/task-state。
- [x] 后端契约测试 RED。
- [x] 后端服务逻辑 GREEN。
- [x] 前端契约测试 RED。
- [x] 前端页面/API GREEN。
- [x] 回归验证、浏览器只读验证、任务收尾与提交。

## Expected Verification

- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`
- `mvn -f backend/pom.xml test`
- `pnpm --dir frontend typecheck`
- `pnpm --dir frontend build`
- `.\scripts\build.ps1`
- Playwright 只读打开 `http://127.0.0.1:48181/`

## 经验门禁

- 命中 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布、备份、恢复、回滚相关校验必须 fail fast；发布包候选必须读取 manifest/checksum/tested，不能只凭目录名。
- 命中 `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`：前端保持紧凑运维控制台风格，不做营销化重设。
- 本任务不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，服务端契约按原版收敛。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed

## Final Verification

- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS
- `mvn -f backend/pom.xml test` -> PASS
- `python -X utf8 scripts\verify_contracts.py` -> PASS
- `pnpm --dir frontend typecheck` -> PASS
- `pnpm --dir frontend build` -> PASS
- `.\scripts\build.ps1` -> PASS
- Browser E2E at `http://127.0.0.1:48181/` -> PASS, screenshot `evidence/runtime-control-standalone-e2e.png`
