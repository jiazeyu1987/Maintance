# 20260724 推送维护仓到 GitHub - Execution Log

- BDD: 推送当前维护仓到指定 GitHub 仓库 -> Given 当前维护仓存在可验证 Git 状态和指定 GitHub 远端, When 执行安全的当前分支推送, Then 远端分支应更新到本地提交或明确报告阻塞原因。
- GREEN: task-bootstrap -> PASS, 已完成只读 UTF-8 bootstrap，读取适用 AGENTS、经验索引和最近任务状态；公共 PowerShell 记忆文件路径不存在，后续仅使用已知 UTF-8/PowerShell 门禁并记录为风险。
- GREEN: experience-preflight -> PASS, 本任务不执行服务器写入、发布、数据库修改、真实 E2E、worktree 合并或清理；Git 推送前仍需完成远端/分支/状态检查，不使用 `&&`、强推或 fallback 远端。
- GREEN: git-preflight -> PASS, 当前分支 `int_main`，原始 HEAD `fe182434475d27200054c9991232d1418c15fd50`；目标 GitHub 仓库 `https://github.com/jiazeyu1987/IntRuoyiMaintance.git` 可访问。
- RED: git push https://github.com/jiazeyu1987/IntRuoyiMaintance.git int_main:int_main -> FAIL, GitHub pre-receive hook 拒绝 `doc/tasks/20260709-codeonly-three-env-head-release/evidence/build-release-v5-result.json`，该已提交 blob 大小 `390728434` bytes，超过 GitHub 100 MB 单文件限制。
- BLOCKER: github-large-file-limit -> 当前已提交历史无法直接推送到 GitHub；按 No-Fallback 策略，未执行历史重写、Git LFS 迁移、强推或快照分支替代推送。
- GREEN: experience-consolidation -> PASS, 已将 GitHub `GH001` / 历史大文件推送阻塞沉淀到 `docs/release-build-preflight-lessons.md`，并在 `docs/experience-index.md` 增加关键词路由。
- AUTHORIZATION: user-recommended-history-rewrite -> 用户回复“推荐”“按照最合适的方式进行”，授权采用推荐的历史重写移除超限文件方案。
- COMMAND_INTENT: isolated-history-rewrite -> 在隔离克隆中移除 GitHub 超限文件历史并推送清理后的 `int_main`，不触碰当前主工作区既有未确认改动。
- GREEN: isolated-history-rewrite -> PASS, 隔离克隆 `C:\Users\BJB110\AppData\Local\Temp\IntRuoyiMaintance-push-rewrite-20260724132247` 使用 `git filter-branch` 移除超限文件历史，清理后 HEAD 为 `9978c0837a5176e4e951c35a8c87625e39930ca6`。
- GREEN: large-blob-scan -> PASS, 对清理后的 `int_main` 可达对象执行 100 MB 阈值扫描，结果 `NONE`。
- GREEN: git push https://github.com/jiazeyu1987/IntRuoyiMaintance.git int_main:int_main -> PASS, 远端创建并随后快进更新 `refs/heads/int_main`，最终远端引用以 `git ls-remote` 实时验证为准。
