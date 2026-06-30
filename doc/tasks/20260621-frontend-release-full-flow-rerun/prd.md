# PRD

## Goal

在不使用接口替代页面动作的前提下，完成一次真实、可追溯、可复核的页面发布全链路，或在高风险前置条件不明确时明确阻断原因并停止执行。

## Scope

- 维护仓真实发布链路相关任务文档、执行日志和测试计划
- 本机运行控制台、业务前后端发布基线核对
- 如前置条件满足，则执行页面 build-release、deploy test、mark-tested、deploy prod、deploy backup
- 每一步的失败记录、修复记录、重跑记录与只读核验证据

## Non-Goals

- 不继续推进上一备份恢复演练任务
- 不用接口直调、命令行直跑发布脚本来替代页面提交
- 不在未明确发布基线时擅自执行新的测试服/正式服/备份服写入

## User or System Scenarios

- 用户要求再次正式走一遍页面真实发布全链路。
- 系统已存在同类链路完整成功证据，需要判断是复用既有结论还是再次发起真实写入。
- 维护仓存在其他任务未收口改动，必须先评估是否允许进入本轮真实环境。

## Functional Requirements

- FR-01：开始新一轮真实写入前，必须记录并明确本次发布基线。
- FR-02：若进入执行阶段，构建/部署/标记测试通过/正式服上线/备份服上线都必须由页面真实动作触发。
- FR-03：每遇到失败，必须先把失败、根因和影响写入执行日志，再修复并从页面重走。
- FR-04：每一步成功后都必须补 operation、manifest、远端 `.env`、镜像和页面入口等只读证据。
- FR-05：若前置条件不足，必须 fail fast，明确阻塞原因与影响，不得靠 fallback 或默认成功继续。

## Non-Functional Requirements

- NFR-01：所有中文文档和日志以 UTF-8 读写。
- NFR-02：高风险动作前必须具备 `experience-preflight` 记录。
- NFR-03：最终结论必须能证明是“本轮真实页面链路一次性通过”，或明确说明未进入执行的阻塞点。

## Dependencies and Constraints

- 命中文档：`release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`login-access.md`、`project-error-prevention.md`
- 当前已知同类完成证据：`doc/tasks/20260620-frontend-release-full-flow/`
- 当前维护仓存在未收口的 `backup-ops` 改动，属于真实发布前必须审视的风险因素
- 正式服和备份服默认高门禁，必须使用已测试通过发布包与 `PROD` 确认语义

## Acceptance Criteria

- AC-01：在任何新的真实写入前，任务文档和执行日志中明确记录本次发布基线与阻塞/放行依据。
- AC-02：若执行真实页面链路，则 build/test/prod/backup 每一步都有真实页面提交证据和 operation 证据。
- AC-03：若执行真实页面链路，则测试服、正式服、备份服都完成远端 `.env`、运行镜像、健康与页面入口核验。
- AC-04：若执行真实页面链路，则正式服和备份服的展厅受保护 URL 边界核验通过。
- AC-05：若本轮不执行真实写入，任务文档、执行日志和最终汇报必须明确指出阻塞前置条件及其影响。
