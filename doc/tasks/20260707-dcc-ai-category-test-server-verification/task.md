# 20260707-dcc-ai-category-test-server-verification

Status: completed

## Task Goal

将 IntRuoyi 当前已提交的 DCC 关联文档 AI 分类修复，按严格测试服验证口径构建为新的 code-only releaseTag，发布到测试服，并确认测试服运行态与发布包 manifest 的后端/前端提交一致。

## Scope

- 仅发布测试服。
- 不执行 mark-tested、正式服、备份服、回滚、恢复或数据清理动作。
- 不从脏维护仓主工作区直接发布；构建输入必须来自干净发布工作区或明确校验的已提交代码。
- 发布口径必须使用单一 releaseTag 串联 build-release -> publish-test -> 测试服运行态验证。

## Expected Inputs

- 后端提交：`fec88bca85c6292bfff3e1c420f5780443801954`
- 前端提交：`ce05b5d6d494410bc2c80d358f17c169cf669a5b`
- 维护仓发布脚本提交：`9aaa5fa`
- 最终发布类型：code-only
- 最终测试服 releaseTag：`release-20260707-1605-dcc-ai-category-test-v5`

## 经验门禁

- 发布链路只认单一 releaseTag，不能拼接旧构建和新部署结果。
- build-release 必须校验 `manifest.json` 的 `sourceRepos`，且后端/前端 `dirty=false`。
- publish-test 必须显式绑定测试服目标，不得漂移到正式服或备份服。
- code-only 不等于跳过发布契约；仍需 SQL/manifest/运行态门禁。
- 测试服运行态验证必须确认 `.env IMAGE_TAG`、后端镜像 tag、前端镜像 tag、后端 health、前端 HTTP。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。本任务只执行发布验证，不修改发布逻辑。
- 是否从根因和长期维护角度解决：是。用真实发布链路证明当前提交在测试服运行，而不是用本地测试替代。
- 是否存在临时补丁或绕过：否。若发布输入或运行态门禁失败，直接阻塞并记录原因。

## BDD Scenarios

- BDD: 当前修复必须以新 releaseTag 进入测试服 -> Given 后端 `fec88bca85c6292bfff3e1c420f5780443801954` 与前端 `ce05b5d6d494410bc2c80d358f17c169cf669a5b` 已提交 When 执行测试服验证 Then 必须构建新的 releaseTag 并发布到测试服，不能复用旧测试服运行标签。
- BDD: 发布包必须可追溯源码提交 -> Given build-release 完成 When 读取发布包 `manifest.json` Then `sourceRepos` 必须包含后端和前端目标提交且 `dirty=false`。
- BDD: 测试服运行态必须匹配 releaseTag -> Given publish-test 成功 When 检查测试服 Then `.env IMAGE_TAG`、后端/前端镜像 tag、后端 health 与前端 HTTP 必须全部通过。

## Milestones

1. 补齐任务文档与高风险经验门禁。COMPLETED
2. 准备干净发布工作区和唯一 releaseTag。COMPLETED
3. 执行 build-release 并校验 manifest/sourceRepos。COMPLETED
4. 执行 deploy-release 并验证测试服运行态。COMPLETED
5. 回写业务任务验证结论。COMPLETED

## Expected Verification

- `build-release` operation 成功或发布脚本返回成功。
- `manifest.json` 中后端/前端提交与本任务输入一致，且 `dirty=false`。
- 测试服当前 releaseTag 等于本任务 releaseTag。
- 测试服后端 health 为 UP，前端 HTTP 为 200。
- 测试租户真实登录后可见 `AI分类` 按钮，点击后显示百分比文本，无进度条，候选文件被分类且候选数下降。
- 测试服数据库确认权限迁移 `20260707_dcc_ai_category_permission_menu` 为 `APPLIED`，测试租户角色具备 `dcc:project-code:update` 与 `dcc:controlled-file:update`。

## Current Status

completed：已用最终 code-only 包 `release-20260707-1605-dcc-ai-category-test-v5` 发布测试服；未执行 mark-tested、正式服、备份服、回滚、恢复或数据清理。

## Final Verification

- GREEN: v5 package contract -> PASS，`manifest.json` 与 `release-manifest.json` 均为 `publishScope=code-only`，不包含数据库 dump 或 MinIO snapshot，包含 `required-sql/20260707_dcc_ai_category_permission_menu.sql`。
- GREEN: test deploy -> PASS，测试服 `.env IMAGE_TAG`、后端镜像、前端镜像均为 `release-20260707-1605-dcc-ai-category-test-v5`，后端 health=`UP`，前端 HTTP=`200`，PDF worker HTTP=`200`。
- GREEN: permission migration -> PASS，`infra_release_migration` 中 `20260707_dcc_ai_category_permission_menu` 状态为 `APPLIED`；测试租户角色拥有 `dcc:project-code:update` 与 `dcc:controlled-file:update`。
- GREEN: real UI verification -> PASS，测试租户 `aoteman` 真实登录 DCC 项目代码页，项目 `1` 点击 `AI分类`，页面显示 `AI分类中 0%`，无 `.el-progress` 进度条，文件 `2054545668044050095` 从候选集中移除。
- GREEN: database result verification -> PASS，文件 `2054545668044050095` 写入 `技术文档 / 未分类 / 未分类文件类型`，项目 `1` 剩余候选数为 `0`。
