# Database Schema Evidence

## Goal And Affected Entities

纠正菜单迁移分类和 MES migration `dependsOn` 元数据，使发布范围与真实 migration 依赖一致；不手工修改数据库或 migration ledger。

## Engine And Migration Tool

- Engine: MySQL（待正式文档/脚本复核）。
- Migration tool: IntRuoyi release migration planner/runner（待正式命令复核）。

## Data Safety And Recovery

- 本任务仅修改已提交 migration metadata/发布预检合同，不直接对生产环境执行任何操作。
- 只允许发布测试服务器；发布前必须完成 scope-aware dry plan 和依赖闭包验证。
- 失败时停止发布并保留旧容器运行态及 operation 证据；不得手工修库或改 ledger。

## BDD / RED / GREEN / Migration Verification / Blockers

待执行。
