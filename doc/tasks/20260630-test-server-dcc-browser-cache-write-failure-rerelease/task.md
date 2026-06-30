# 任务：测试服 DCC 受控浏览缓存写入失败补发版

- Task ID: `20260630-test-server-dcc-browser-cache-write-failure-rerelease`
- Workspace: `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc`
- Created: `2026-06-30`
- Current Status: `completed`

## Task Goal

在干净维护 worktree 中把 runtime-control 的发布输入切到本次 DCC 浏览器缓存修复对应的前端干净 worktree，执行真实 `build-release -> publish-test`，让测试服务器 `172.30.30.58` 的运行态升级到包含轻量目录缓存逻辑的新 bundle，并用真实页面复验 `DCC 受控浏览本地缓存写入失败，请检查浏览器本地存储权限。` 不再出现。

## Scope

- 维护仓：`D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc`
- 后端发布输入：`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260630-ec6514e`
- 前端发布输入：`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260630-dcc-cache-rerelease`
- 目标环境：测试服务器 `172.30.30.58`
- 允许动作：真实 `build-release`、真实 `publish-test`、测试服只读版本核验、官方登录预检、DCC 页面真实回归

## Non-Scope

- 不执行 `mark-tested`
- 不触达正式服或备份服
- 不手工改测试服容器内静态资源、数据库或浏览器本地存储绕过发布链路

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc\doc\tasks\20260630-build-release-local-runtime-guard\task.md`
- 状态：`blocked`
- 处理说明：用户当前优先级已经切到测试服 DCC 浏览页故障补发版；上一维护仓任务已在主工作区显式阻塞，本次只承接测试服补发版。

## 当前状态

- `completed`
- 测试服当前 `.env IMAGE_TAG=release-20260630-141004-dcc-cache-rerelease`。
- 测试服运行镜像已切换到 `intruoyi-backend:release-20260630-141004-dcc-cache-rerelease` 与 `intruoyi-frontend:release-20260630-141004-dcc-cache-rerelease`。
- 真实登录和 DCC 页面回归均确认问题消失。

## 经验门禁

- `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc\docs\experience-index.md`
  - 命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 发布“已提交版本”前必须显式核对 runtime-control 当前 `repo-root` / `frontend-root` 指向的就是最新干净 worktree。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - 发布成功判定必须同时看 operation、manifest、远端 `.env IMAGE_TAG`、运行镜像、health 与前端入口。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 测试服目标统一为 `172.30.30.58` 与 `/opt/intruoyi/runtime`；只在用户授权范围内写入测试服。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
  - 测试服真实验证前必须先跑官方 `login-preflight.mjs`，不得用旁路登录替代正式结论。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 发布输入必须来自干净 worktree；不得用主工作区脏改直接出包。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；通过把维护仓发布输入切回正确的前端干净 worktree，并用正式发布链路更新测试服运行态。
- `是否存在临时补丁或绕过`：否；不手工替换测试服 JS 文件，不直接 SSH 改静态资源。

## 里程碑

1. M1：补齐干净维护 worktree 的任务文档、经验门禁与 experience-preflight。`completed`
2. M2：确认当前维护仓 `frontend-root` 误指向旧 worktree，并锁定新前端修复提交。`completed`
3. M3：更新维护仓本地发布配置并重启 runtime-control。`completed`
4. M4：执行真实 `build-release -> publish-test`。`completed`
5. M5：核对测试服运行版本并做真实 DCC 页面回归。`completed`

## Expected Verification

- `http://127.0.0.1:48181/actuator/health`
- 真实 `build-release` operation `SUCCESS`
- 真实 `publish-test` operation `SUCCESS`
- 测试服 `.env IMAGE_TAG=<本次 releaseTag>`
- 测试服 backend/frontend 镜像 tag=`<本次 releaseTag>`
- `node D:\ProjectPackage\Int\IntRuoyi\scripts\preflight\login-preflight.mjs --base-url http://172.30.30.58:8081 --tenant 测试租户 --username aoteman --password 111111 --target-path /dcc/controlled-file/browser --target-text 刷新列表`
- 真实页面验证：DCC metadata localStorage 不再包含嵌套 `children`，且不再出现缓存写入失败提示

## Final Verification Result

- `http://127.0.0.1:48181/actuator/health` -> `{"status":"UP"}`
- `build-release` operation：`op-2026-06-30T061212574888700Z-6df2be09-089c-4d0f-9c3b-ea1a3f492fe6` -> `SUCCESS`
- `publish-test` operation：`op-2026-06-30T063029209792400Z-8b3bd5dd-5120-44b6-bf7d-4961956cbef8` -> `SUCCESS`
- `release-packages` -> `release-20260630-141004-dcc-cache-rerelease` `AVAILABLE`
- 测试服 `.env IMAGE_TAG=release-20260630-141004-dcc-cache-rerelease`
- 测试服运行镜像：
  - `intruoyi-backend:release-20260630-141004-dcc-cache-rerelease`
  - `intruoyi-frontend:release-20260630-141004-dcc-cache-rerelease`
- `http://172.30.30.58:48081/actuator/health` -> `{"status":"UP"}`
- `http://172.30.30.58:8081/` -> `200`
- `node D:\ProjectPackage\Int\IntRuoyi\scripts\preflight\login-preflight.mjs --base-url http://172.30.30.58:8081 --tenant 测试租户 --username aoteman --password 111111 --target-path /dcc/controlled-file/browser --target-text 刷新列表` -> PASS
- 真实 DCC 页面验证：
  - 无 toast/dialog/pageerror
  - localStorage `dcc.controlledFile.browser.metadata:*` `rawLength=35686`
  - `rootHasChildrenField=false`
  - `childHasChildrenField=false`

## Current Blockers

- 无。
