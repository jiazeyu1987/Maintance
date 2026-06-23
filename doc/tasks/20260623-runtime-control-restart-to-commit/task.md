# 任务：运行控制台更新到已提交版本

## Goal

把本机运行控制台 `127.0.0.1:48181` 更新到当前已提交版本，使其加载这次新增的左下角版本栏和后端版本字段。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-runtime-control-version-dock\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成提交与验证，本任务直接做本机控制台重启更新。

## Scope

- 构建：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\build.ps1`
- 启动：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\start.ps1`
- 验证：
  - `http://127.0.0.1:48181/`
  - `http://127.0.0.1:48181/admin-api/infra/runtime-control/release-status`

## Non-Scope

- 不改业务代码。
- 不改测试服/正式服/备份服。
- 不做发布到远端服务器。
- 不修改数据库。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 强制门禁摘录：
  - 运行控制台只有在重新构建并重启后才算加载新逻辑，不能把源码提交当成当前 48181 进程已更新。
  - 构建前先释放 target jar 锁。
  - 本任务仅更新本机控制台，不触发远端服务器写入。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。以正式构建和重启让当前进程加载已提交版本。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 重新构建并重启本机运行控制台 -> Given 当前提交已包含版本栏 When 执行 build 并启动 48181 Then 页面和 release-status 应返回新版本字段。`
- `BDD: 旧进程被替换 -> Given 48181 仍运行旧 jar When 停止旧进程并启动新 jar Then 进程命令行应切换到最新构建产物。`

## Milestones

1. 记录本地更新任务和验收点。`COMPLETED`
2. 停止旧 48181 进程并释放 jar 锁。`COMPLETED`
3. 执行构建与启动。`COMPLETED`
4. 复核页面资源与 API 字段。`COMPLETED`

## Expected Verification

- `powershell -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\build.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\start.ps1`
- `Invoke-WebRequest http://127.0.0.1:48181/`
- `Invoke-WebRequest http://127.0.0.1:48181/admin-api/infra/runtime-control/release-status`

## Current Status

COMPLETED：已完成本机运行控制台重建与重启，当前 48181 已加载本次提交版本，保留运行 PID 为 `35752`。

## Final Verification

- `powershell -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\build.ps1` -> PASS。
- `Invoke-WebRequest http://127.0.0.1:48181/` -> PASS，新资源 `index-BVR1hDry.js` 已加载。
- `Invoke-WebRequest http://127.0.0.1:48181/admin-api/infra/runtime-control/release-status` -> PASS，已返回 `test/prod/backupCurrentReleaseTag`。
- Playwright 真实页面快照 -> PASS，左下角版本栏已显示。
- 最终运行进程复核 -> PASS，PID `35752` 监听 `48181`，命令行指向最新构建 jar。
- `task-closeout-cleanup` preview/apply -> PASS，仅清理本次旧启动临时日志。
