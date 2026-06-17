# 执行日志: 构建发布耗时问题经验沉淀

- 用户需求：`将经验沉淀到文档里,下次不要遇到同样的问题`。
- `BDD: 发布经验可复用 -> Given 20260617 构建发布曾因基础镜像、迁移依赖和本机锁多次失败, When 后续 Agent 读取维护仓库经验文档, Then 能在发起真实 E2E 构建前按清单预检并提前阻断。`
- 范围：仅更新文档；不发布、不重启、不备份、不恢复、不回滚、不写远端服务器和数据库。
- `GREEN: evidence-collection -> PASS，使用 fupan 脚本从 20260617-e2e-build-publish-test 的 task、execution-log、verification-report 生成 candidate-error-evidence.md。`
- `GREEN: memory-update -> PASS，新增 docs/agent-memory/project-error-prevention.md，项目短记忆 309 字，覆盖发布前 Docker/迁移/锁预检、TDD 提交门禁和发布完成联合验证。`
- `GREEN: release-preflight-doc -> PASS，新增 docs/release-build-preflight-lessons.md，写入发布前必做预检、发布完成判定和重试规则。`
- `GREEN: experience-index -> PASS，docs/experience-index.md 已新增构建发布耗时/真实 E2E 发布预检路由和项目错误预防短记忆路由。`
- `GREEN: doc-validation -> PASS，rg 校验索引、Docker、迁移策略门禁、jar 锁、TDD 钩子、operation SUCCESS、IMAGE_TAG、Playwright 均能命中新文档。`
- `GREEN: task-closeout-cleanup-preview -> PASS，保留 task.md、execution-log.md、candidate-error-evidence.md；无删除项、无阻塞、无警告。`
- `BLOCKER-CLEARED: task-closeout-status-field -> apply 初次阻塞，因为 task-closeout-cleanup 只识别英文 Current Status；已补充 Current Status=completed。`
- `GREEN: task-closeout-cleanup-apply -> PASS，保留 task.md、execution-log.md、candidate-error-evidence.md；无删除项、无阻塞、无警告。`
