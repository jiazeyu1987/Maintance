# 任务：提交当前前后端代码

## 任务目标

在不混入无关改动、临时文件或半成品任务的前提下，审计当前前后端真实仓库的未提交状态，按任务边界完成必要验证，并将可提交的当前代码分别提交到所属 Git 仓库。

## 当前状态

`COMPLETED`

## 上一任务检查

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-int-main-workspace-normalization\task.md`
- 状态：`BLOCKED`
- 处理：
  - 上一任务已经明确阻塞原因：后端原始目录仍保留本地现场，不能直接切回真正 `int_main`。
  - 本任务不处理 worktree 恢复，只在现有现场基础上做“哪些代码可以安全提交”的提交隔离与收口。

## 用户要求与执行边界

- 用户要求：
  - 提交当前前后端的所有代码。
- 当前任务授权：
  - 允许在本机维护仓、后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 与前端仓 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 审计、验证、暂存并提交当前任务相关代码。
  - 允许补齐必要的任务文档、执行日志与请求命令日志。
- 禁止范围：
  - 不把无关用户改动、临时环境文件或未验证半成品混入提交。
  - 不用 `reset --hard`、静默回退、fallback 或“先提交再说”绕过仓库门禁。
  - 不操作服务器、测试服或正式服。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
- 本任务强制门禁摘录：
  - 混合工作区提交前必须先核对真实前后端仓库状态，不能把根目录 Git 状态当成提交依据。
  - 同文件或同暂存区混入其他任务 hunk 时，不得整批提交；必须按任务边界拆分、验证和提交。
  - 提交前要先确认哪些内容是可验证可落地的正式改动，哪些仍是未完成支线或本地临时文件。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是。通过逐仓库、逐任务核对和验证后再提交，避免把混合现场一次性糊进提交历史。
- `是否存在临时补丁或绕过`：否

## BDD 场景

- `BDD: 只提交已识别归属的当前代码 -> Given 前后端真实仓库存在混合未提交现场 / When 执行本次提交任务 / Then 只有已核对归属、通过必要验证、可独立解释的代码才允许进入提交。`
- `BDD: 本地临时文件不得冒充前端代码提交 -> Given 前端仓库当前只有本地环境文件或无业务改动 / When 用户要求提交当前前后端代码 / Then 系统必须明确说明“没有可提交的前端业务代码”，而不是把临时文件硬塞进提交。`
- `BDD: 未完成支线不得与已验证任务混提 -> Given 后端仓库同时存在已验证任务与进行中支线 / When 生成提交 / Then 必须按任务边界拆分，未完成支线要么补齐验证后单独提交，要么明确阻塞。`

## 里程碑

1. 建立维护仓提交任务台账并记录经验门禁。`DONE`
2. 审计真实前后端仓库当前 staged/unstaged/未跟踪状态。`DONE`
3. 按任务边界核对后端当前代码归属与验证证据。`DONE`
4. 提交可放行的后端代码。`DONE`
5. 确认前端是否存在可提交业务代码并收尾。`DONE`

## 预期验证

- `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro status --short --branch`
- `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 status --short --branch`
- 对每组后端改动执行其任务文档声明的定向验证命令。
- 提交后重新核对各仓库 `git status --short`，确认只留下本次未授权提交的现场或本地临时文件。

## 完成结果

- 后端 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 已按任务边界提交完成，当前工作区干净。
- 前端 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 已提交业务改动，当前仅剩未跟踪本地环境文件 `.env.merged-e2e`，未纳入提交。
- 未操作服务器、测试服或正式服。
