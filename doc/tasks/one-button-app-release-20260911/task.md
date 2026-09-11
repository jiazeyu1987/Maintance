# one-button-app-release-20260911

## Task Goal

设计“按钮化、程序化、不可变安装包”的发布 workflow：标准安装包固定为 `PublishScope=app-release`，只包含程序升级所需制品和版本化迁移，不包含 MySQL 全量 dump、MinIO 快照/同步、DCC object inventory、runtime data 或秘密配置。

## Milestones

1. [completed] 梳理现有运行控制台、发布脚本、R31-R44 失败证据和已验证 release line。
2. [completed] 产出 PRD，定义三按钮 workflow、状态机、授权边界、包边界和错误码。
3. [completed] 产出测试计划，覆盖构建前门禁、不可变包、测试服发布、正式服晋级守卫、R31-R44 防复发用例。
4. [completed] 完成文档结构校验和独立规划评审，明确实施前置条件。
5. [blocked] 后续在独立实施 worktree 中按 P1-P5 执行，不直接在当前脏主工作树改实现。

## Expected Verification

- PRD 和测试计划结构完整，acceptance id 全覆盖。
- workflow 明确排除 with-data、全量数据库和 MinIO 同步。
- 每个阶段有 fail-fast、证据、恢复和授权边界。
- P1 前置条件未满足时不得开始实现。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；用正式 workflow、状态机和门禁替代人工反复打包。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

- 标准程序包只能使用 `app-release`，with-data 仅属于显式数据发布/备份恢复流程。
- UI/API 不允许操作者自由填写服务器、NAS、MinIO、repo root、LocalCacheRoot 或 releaseTag。
- 构建前必须完成 source freeze、schema-only 迁移演练、target readonly preflight、依赖/前端模块解析、manifest 和 package digest 门禁。
- 同一个 releaseTag/package digest 只能构建一次，测试服和正式服必须消费同一不可变包。
- R31-R44 失败必须转换为可执行回归，不得靠人工记忆避免复发。
- 正式服真实写入必须另行显式授权并要求 PROD 确认。

## Current Status

blocked

规划文档已通过独立复审；功能尚未实现。规划期间另一发布线程已完成 R44 测试服发布与页面验证，本任务未执行该发布，也未触碰其 closeout。

## Verification Evidence

- `validate_artifacts.py`: `status=ok`, 0 errors, 0 warnings。
- CI/CD evidence validator: PASS。
- PRD: 5 phases、32 acceptance IDs；test plan: 15 cases、32/32 acceptance coverage。
- Independent planning review: final PASS after three review rounds。
- UTF-8、trailing whitespace 与 diff checks: PASS；未运行产品构建、发布或服务器写入。

## Blockers

- P1 实施前必须创建独立任务 worktree，不能在当前脏 `int_main` 主工作区直接改实现。
- 需要审查并融合已验证维护线 `8080c0d` 与当前 `int_main` 的分叉差异。
- 当前主工作区存在 `frontend/` 删除和其它脏改动，实施前必须确认归属，不得覆盖。
- 真实测试服写入需当次授权；正式服真实写入不在当前授权范围。
- 项目规定的 Playwright 1.60.0 权威路径当前缺少依赖与可执行文件；P4/P5 在恢复前阻塞，禁止临时下载或换版本兜底。

## Artifacts

- PRD: `doc/tasks/one-button-app-release-20260911/prd.md`
- Test plan: `doc/tasks/one-button-app-release-20260911/test-plan.md`
- Execution log: `doc/tasks/one-button-app-release-20260911/execution-log.md`
- State: `doc/tasks/one-button-app-release-20260911/task-state.json`
- Test report: `doc/tasks/one-button-app-release-20260911/test-report.md`
