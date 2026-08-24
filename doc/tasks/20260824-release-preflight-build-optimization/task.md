# 20260824 发布前置检查与构建依赖复用优化

## Task Goal

将近期测试服发布中反复暴露的迁移、Spring、PowerShell/SSH、JSON 报告、对象存储和 worktree/控制台身份问题前置到可执行的构建/发布检查阶段，并消除同一冻结 worktree 内重复安装前端依赖的浪费。优化必须 fail fast，不引入 fallback、静默重试或旧产物复用。

## Milestones

1. 读取适用发布经验，盘点现有 preflight、构建脚本和测试入口，冻结本任务改动边界。
2. 先补 BDD 场景与 RED 测试，证明现有流程无法拦截目标问题或会重复安装依赖。
3. 实现可复用的发布前置检查与构建依赖复用，保持现有发布范围和真实运行态验收契约。
4. 运行 GREEN、回归和静态检查，审计日志/凭据脱敏及任务外改动边界。
5. 更新长期发布经验入口，记录 ready_for_closeout、清理预览和最终验证结果。

## Expected Verification

- 现有 preflight 继续覆盖迁移元数据、PowerShell/SSH、JSON fixture、对象存储绑定和控制台身份；本任务新增临时表 reopen/collation、Spring 多构造器和前端依赖状态门禁。
- 构建脚本在同一冻结 worktree 内只安装一次依赖，并在构建阶段复用已安装依赖；依赖缺失、状态漂移或安装失败仍直接失败。
- 现有发布脚本、manifest、operation 和仅测试服范围契约不回退。
- `execution-log.md` 记录 BDD、RED、GREEN、回归命令和剩余阻塞。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；所有前置检查失败直接阻塞，不复用旧产物、不自动重试。
- 是否从根因和长期维护角度解决：是；使用共享检查入口、真实命令/fixture 和冻结 worktree 依赖状态，避免按任务复制临时判断。
- 是否存在临时补丁或绕过：否；仅修改正式维护脚本、测试和经验文档，不修改测试数据或服务器状态。

## 经验门禁

- Trigger：发布流程、build-release、publish-test、前端依赖安装、迁移 policy、Spring context smoke、PowerShell/SSH/JSON 命令契约发生变化。
- Preflight check：先读取 `docs/experience-index.md` 命中的 `release-build-preflight-lessons.md`、`test-release-preflight.md`、`powershell-preflight-lessons.md` 和 `E:\IntRuoyi\docs\powershell-memory.md`；运行本任务 RED/GREEN 前不执行真实服务器写入。
- Blocker：发现并发任务文件/进程冲突、无法证明检查使用真实执行路径、依赖安装状态不确定、测试失败或日志含凭据时停止。
- Verification：记录静态测试、构建脚本测试、`git diff --check`、脱敏扫描和目标文件 staged 清单。
- Forbidden action：禁止 `git add -A`、禁止修改当前发布线程的 operation/worktree、禁止以 mock/旧镜像/旧 tag 掩盖失败、禁止吞异常或自动重试。
- Evidence：本任务 `execution-log.md`、测试输出、目标脚本 diff 和更新后的发布经验文档。

## Current Status

completed

## Milestone Status

- Milestone 1: completed；已完成只读 bootstrap、经验索引命中文档和代码入口盘点，确认当前并发发布任务边界。
- Milestone 2: completed；已补 BDD 和 SQL/依赖/Spring 契约 RED 测试。
- Milestone 3: completed；已实现 SQL temp-table gate、Spring constructor gate、应用前端依赖 preflight 和维护构建依赖 stamp 复用。
- Milestone 4: completed；34 条新增/相邻测试、PowerShell AST、目标 diff 检查通过；完整仓库验证受并发 frontend 删除阻塞并已记录。
- Milestone 5: completed；已更新长期发布经验入口，task-closeout-cleanup preview/apply 均通过，任务附属 pytest 临时目录已删除。

## Final Verification

- `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_spring_constructor_contract.py -q --basetemp <task-dir>` -> 34 passed。
- PowerShell AST 解析 `scripts/build.ps1`、`scripts/prepare-frontend-dependencies.ps1`、`ops/deploy/publish-int-ruoyi.ps1` -> PASS。
- task-closeout-cleanup preview/apply -> PASS；保留本任务 `task.md`、`execution-log.md`，删除 `.tmp-pytest/`。
- 完整仓库 `verify_contracts.py` 和前端回归仍因并发任务删除 frontend 文件阻塞，详见 execution-log；未恢复并发内容。

## Cleanup Candidates

- `.tmp-pytest/`
