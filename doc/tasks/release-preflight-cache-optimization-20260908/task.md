# 发布预检前移与构建缓存优化

## Task Goal

增加构建前发布资格预检，并为 Docker 应用镜像建立输入绑定、可验证失效的构建缓存，减少服务器阶段晚失败和重复完整构建。

## Milestones

- [completed] M1：PRD/test plan 与设计审查。
- [completed] M2：逐阶段严格 TDD 实现。
- [completed] M3：独立测试与回归。
- [completed] M4：提交、融合与收尾。

## Expected Verification

- 预检结论早于 Maven、前端和 Docker 构建。
- 预检证据绑定源码、迁移/SQL 和 target-state，漂移即失败。
- Docker 缓存只在完整输入指纹一致时命中，且不绕过最终包完整性校验。
- 不执行真实发布或远程写入。

## 经验门禁

- Trigger：target-state 前移、preflight-plan、BuildKit 缓存、反复打包。
- Preflight check：严格区分静态门禁、目标只读状态和昂贵构建；缓存键覆盖 Dockerfile、上下文、基础镜像 digest 与参数。
- Blocker：证据不可绑定、缓存失效不完整、需要 fallback 或与并发改动重叠时停止。
- Verification：本地 fixture、真实 PowerShell/Python/JDK17/Node、独立 tester。
- Forbidden action：禁止跳过预检、复用陈旧证据、关闭最终哈希或访问正式服。
- Evidence：PRD、test plan、execution log、test report、task state。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是。
- 是否存在临时补丁或绕过：否。

## Worktree

- Path: `D:/ProjectPackage/Int/IntRuoyiWorktrees/release-preflight-cache-optimization-20260908/m`
- Branch: `codex/release-preflight-cache-optimization-20260908`
- Baseline: `20b6328afb36131cca31ee4425fbc543d2e9c9ff`
- Ports: 未启动服务，不登记端口。

## Current Status

completed

## Closeout Evidence

- `f254555`、`8fb5cd8`、`5ff914b`、`1f17a63` 已 fast-forward 融入 `int_main`。
- 任务 worktree 与主线同为 `1f17a63`、状态 clean 后移除；Git 注册和物理路径均不存在。
- `task-closeout-cleanup` 在 linked worktree preview 因主工作区并发脏改动保护而阻断；显式 fast-forward 和 worktree 删除后，在主工作区 preview=ready、apply=applied，无 blocked/warnings。
- 系统 TEMP 下本任务 pytest 目录已删除。
- `project-experience-consolidation` 已合并到现有发布经验文档和索引，未新建长期经验文档。

## Final Verification

- Spec completion 与 test-report schema validation PASS；T1-T10、P1-AC1..P2-AC5 全部完成。
- 独立 worktree：focused 96、full pytest 188、JDK17 Maven 26、Node 6、PowerShell AST PASS。
- 融合主工作区：preflight/cache + P0 governance pytest 99 PASS，Node 6 PASS，Python compile 与 PowerShell AST PASS。
- Maven 首轮复现 fixture 时间碰撞后，以显式 UTC 修复；目标测试连续 3/3 PASS，全 Maven 26 PASS。生产 comparator 未修改。

## Completed Work

- P1：build-release 在 required SQL staging 后、Maven/frontend/Docker 前 fresh 采集测试服 migration ledger，生成并复验输入绑定 evidence。
- P2：backend/frontend 移除 `--no-cache`，启用 Docker 原生内容缓存；构建前后复算 Dockerfile/COPY context/base digest/build args，实际镜像身份写入包内 evidence。
- P0 安装包逐文件哈希、packageDigest、docker save、manifest 与 NAS copy 后复验保持无条件执行。

## Verification Evidence

- Independent blind-first-pass: T1-T10、P1-AC1..P2-AC5 全部 PASS。
- Focused pytest 96 passed；full pytest 188 passed。
- JDK17 Maven 26 passed；Node 6 passed；PowerShell AST PASS。
- 未连接 SSH、NAS、Docker daemon、数据库或服务器，未执行真实 build-release/publish。

## Implementation Commit

- `f254555`：前移发布预检并启用构建缓存。
- `5ff914b`：为发布说明回归 fixture 固定明确 UTC 时间，消除 Windows 时钟碰撞导致的间歇失败。

## Remaining Blockers

- 无实现或本地测试阻塞；真实测试服 SSH/容器/迁移台账与真实 Docker cache hit 需在后续获得发布授权时通过一次真实 build-release 验证。

## Cleanup Keep

- `doc/tasks/release-preflight-cache-optimization-20260908/task.md`
- `doc/tasks/release-preflight-cache-optimization-20260908/prd.md`
- `doc/tasks/release-preflight-cache-optimization-20260908/test-plan.md`
- `doc/tasks/release-preflight-cache-optimization-20260908/task-state.json`
- `doc/tasks/release-preflight-cache-optimization-20260908/execution-log.md`
- `doc/tasks/release-preflight-cache-optimization-20260908/test-report.md`
- `doc/tasks/release-preflight-cache-optimization-20260908/bug-regression-evidence.md`
