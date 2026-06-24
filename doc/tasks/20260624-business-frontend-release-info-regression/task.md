# 任务：发布包向业务前端注入版本与变更信息

## 目标

修复三环境重新发布后业务前端看不到版本号和版本变更信息的问题。发布脚本必须把本次发布包的 releaseTag、changeSet 和 sourceRepos 写入前端静态资源，确保业务前端页面可读取。

## 上一任务检查

- 上一相关任务：`doc/tasks/20260624-head-full-release/task.md`
- 状态：COMPLETED。
- 补充说明：该任务验证的是维护控制台 `release-status` 能看到三环境版本与 notes；用户反馈的是业务前端页面不显示，因此本任务补齐业务前端发布信息注入。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 发布包 manifest 必须证明 releaseTag、changeSet、sourceRepos 与构建输入一致。
  - 发布完成必须验证真实页面能看到当前版本。
  - 当前脚本变更说明只有默认 summary，需要让页面至少能读取本次 manifest 级别说明。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - 测试服先发布并验证，通过后才能继续正式服和备份服。
  - 远端镜像 tag、发布 manifest 与页面显示版本必须一致。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；缺少 release-info 静态文件时前端暴露错误状态，发布脚本生成失败时直接失败。
- `是否从根因和长期维护角度解决`：是；发布脚本生成前端可读的 release-info 文件，业务前端统一读取。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 发布包注入发布信息 -> Given 构建 code-only 发布包 When 前端 dist 构建完成 Then dist/release-info.json 包含 releaseTag、changeSet、sourceRepos。`
- `BDD: 三环境页面版本一致 -> Given 测试服、正式服、备份服使用同一发布包 When 用户打开业务前端 Then 页面显示的 releaseTag 与远端 IMAGE_TAG 一致。`

## 里程碑

1. 写入任务文档与 RED 脚本契约测试。`COMPLETED`
2. 修改发布脚本生成前端 release-info 静态文件。`COMPLETED`
3. 运行脚本契约测试。`COMPLETED`
4. 提交维护仓本任务改动。`COMPLETED`

## 预期验证

- `node scripts/tests/publish_release_info_contract.test.mjs` 通过。

## 当前状态

COMPLETED：发布脚本已在前端 dist 生成 `release-info.json`，内容包含 releaseTag、packageId、createdAt、publishScope、changeSet 和 sourceRepos；manifest 与业务前端静态文件复用同一 changeSet 生成函数。

## 验证证据

- `node scripts/tests/publish_release_info_contract.test.mjs` -> RED：发布脚本未包含 `Write-FrontendReleaseInfo`，未写入 `release-info.json`。
- `node scripts/tests/publish_release_info_contract.test.mjs` -> GREEN：2 tests passed。
- PowerShell `[scriptblock]::Create(...)` -> GREEN：脚本语法 OK。
