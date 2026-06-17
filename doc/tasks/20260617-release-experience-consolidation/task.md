# 任务: 构建发布耗时问题经验沉淀

## 任务目标

将 `20260617-e2e-build-publish-test` 构建发布过程中暴露的重复风险沉淀到可复用文档中，避免后续发布再次在 Docker 基础镜像、迁移依赖、本机 jar 锁、operation 证据和提交门禁上反复踩坑。

本任务只更新文档，不执行发布、重启、备份、恢复、回滚、SSH 写入或数据库写入。

## 经验门禁

- `docs/experience-index.md`：任务开始先读取索引，并只打开命中的经验文档。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布必须通过运行控制台真实前端动作；发布完成必须由 operation、manifest、远端 tag、健康检查和真实页面共同证明；迁移门禁、本机运行实例、Docker 基础镜像和发布包 manifest 都是发布前置条件。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。把耗时根因转成下一次发布前可执行的预检清单和项目记忆。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 发布经验可复用 -> Given 20260617 构建发布曾因基础镜像、迁移依赖和本机锁多次失败, When 后续 Agent 读取维护仓库经验文档, Then 能在发起真实 E2E 构建前按清单预检并提前阻断。`

## 里程碑

- [x] 创建任务文档。
- [x] 收集候选证据。
- [x] 更新维护仓库经验文档与项目记忆。
- [x] 运行文档校验。
- [x] 运行收尾清理。
- [x] 提交本任务文档改动。

## 复盘结果

### 已采纳

- Docker 基础镜像拉取问题沉淀为发布前预拉和 inspect 基础镜像。
- `release-migration dependsOn` 格式问题沉淀为“依赖写 migrationId，不带 `.sql`”。
- 本机 Maven target / jar 锁沉淀为构建前 `clean` 预检和释放 target jar 锁。
- 提交钩子问题沉淀为 SQL/script 变更前先跑 TDD 钩子、日志写裸 `RED/GREEN`、SQL 变更配 `script/tests`。
- 发布完成判定沉淀为 operation、manifest、远端 tag、容器、健康检查、迁移状态和真实浏览器入口共同证明。

### 未写入长期基线

- 具体 releaseTag、operationId、Docker digest、测试服实时容器运行时长只保留在任务证据中，不写入长期经验。
- 远端登录未执行的原因只作为本次边界记录，不升级为新规则；远端账号仍以 `login-access.md` 为准。

## 预期验证

- `candidate-error-evidence.md` 或等效证据引用本次发布执行日志。
- 经验文档包含可执行预检项，不只描述事故。
- `docs/experience-index.md` 能路由到新增经验文档。
- `task-closeout-cleanup` preview/apply 通过。

## Cleanup Keep

- `doc/tasks/20260617-release-experience-consolidation/candidate-error-evidence.md`

## 最终验证

- `GREEN: evidence-collection -> PASS`，候选证据来自本次构建发布任务文档、执行日志和验收报告。
- `GREEN: doc-validation -> PASS`，`rg` 命中索引、新文档和项目记忆中的关键预检项。
- `GREEN: project-memory-size -> PASS`，项目短记忆 309 字，小于 800 字限制。
- `GREEN: task-closeout-cleanup-preview -> PASS`，保留 task、execution-log 和 candidate-error-evidence，无删除项、无阻塞、无警告。
- `GREEN: task-closeout-cleanup-apply -> PASS`，无删除项、无阻塞、无警告。

## 当前状态

completed

## Current Status

completed
