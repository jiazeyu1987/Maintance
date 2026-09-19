# 发布耗时优化

## Task Goal
按照用户指定 6 步优化发布脚本：默认 code-only、拆分代码/数据快照包、减少重复全量扫描、NAS 上传使用可观察复制、增加阶段耗时/心跳、with-data 显式门禁。

## Milestones
- [x] M1 建立发布耗时优化任务文档、经验门禁与 BDD/TDD 记录。
- [x] M2 为发布脚本补充/调整自动化测试，先复现当前慢路径风险。
- [x] M3 修改 `ops/deploy/publish-int-ruoyi.ps1` 和相关维护代码，实现 6 步优化。
- [x] M4 运行目标测试与静态校验，确认无 fallback、无 mock 成功、无语法错误。
- [x] M5 更新任务证据、请求命令日志和经验沉淀，完成收尾。
- [x] M6 对已提交实现执行独立静态逻辑审查；发现问题时先补回归测试再修复。

## Expected Verification
- 运行与发布脚本相关的 pytest/PowerShell 静态测试。
- 验证默认 build-release 不再隐式携带数据库和 MinIO 数据。
- 验证 with-data 需要显式确认或强制参数。
- 验证 NAS copy 与长耗时阶段存在可观察日志。
- 对发布范围、manifest、完整性校验、NAS 复制和部署分支做独立逻辑审查；无阻塞问题才允许收口。

## Current Status
ready_for_closeout

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；通过发布范围默认收敛、数据包拆分、扫描复用和可观察复制解决耗时根因。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- `release-build-preflight-lessons.md`：发布加速不得跳过 releaseTag、manifest、sourceRepos dirty=false、镜像 tag、health、HTTP、版本说明和真实页面验收。
- `release-build-preflight-lessons.md`：with-data 发布必须在昂贵构建前确认 DCC 对象一致性和工具镜像，不得用 code-only 或跳过 inventory 绕过数据问题。
- `test-release-preflight.md`：仅测试服发布成功范围止于同一 releaseTag 的 `build-release -> publish-test` 与运行态验证；本任务不执行真实发布。
- `powershell-memory.md`：PowerShell 串联命令不用 `&&`，中文读写必须显式 UTF-8。

## Review Scope
- 本次只审查 `6639128` 触及的发布脚本、manifest schema/validator、治理模块和合同测试，以及它们在当前工作区中的实际组合逻辑。
- 不执行真实 `build-release`、`publish-test`、NAS 上传、服务器写入、数据库写入或 MinIO 写入。
- reviewer 只读审查；worker 仅修复 reviewer 明确列出的阻塞项。

## Cleanup Candidates
- `.tmp-pytest-release-duration-static-review`
- `.review-fix-loop/runs/20260910-release-duration-static-review`
