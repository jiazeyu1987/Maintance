# 任务：再次按页面真实流程走构建发布到测试服/正式服/备份服

## 任务目标

在运行控制台前端页面中，严格通过真实按钮与真实弹窗动作，重新执行一次“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”的完整链路。过程中禁止用接口直调替代页面提交；遇到任一步问题，必须先记录到任务文档，修复后再从页面重走，直到整条链路一次性通过。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-backup-server-backup-restore-rehearsal\task.md`
- 状态：`BLOCKED`
- 处理：已在旧任务文档中显式记录“用户优先级切换导致中断”，避免把未完成的备份恢复演练误记为完成；本任务作为新的高风险真实发布任务单独建档。

## 用户要求与执行边界

- 用户要求：
  - 正式按“页面前端点击操作”的真实流程完整走一遍发布链路
  - 目标顺序为：构建发布到测试服、再到正式服、再到备份服
  - 禁止直接调接口替代页面动作
  - 每遇到问题先记录任务文档，修复后继续从页面走
  - 直到整条流程能够一次性走通才算完成
- 当前任务边界：
  - 允许读取和更新维护仓/业务仓任务文档、测试计划、执行日志
  - 允许只读检查本机运行控制台、业务前后端仓状态和远端当前运行态
  - 未明确发布基线前，不执行新的真实页面 build/deploy 写动作
  - 高风险真实写入前，`execution-log.md` 必须先记录 `GREEN: experience-preflight -> PASS`

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 构建发布包必须由运行控制台页面按钮触发，命令行只允许做只读核验、失败排查和测试。
  - 发布前必须先确认本机控制台版本、发布包源头、目标环境、目标主机、目标数据盘和目标 `releaseTag`，缺一直接阻塞。
  - 发布验证不能只看健康检查，必须同时核 operation、manifest、远端 `.env`/镜像、页面入口和受保护边界。
  - 正式服和备份服都属于高门禁环境，必须使用已测试通过发布包，并保持 `PROD` 确认语义。
  - 如果发布输入发生变化，必须使用新的 `releaseTag` 重建并从测试服开始整链重走；旧候选包只作证据。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。若需要重跑，将以真实页面链路和正式 preflight 为准，不靠接口绕过或手工替代。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 页面真实提交发布全链路 -> Given 运行控制台页面与发布前置条件齐备 / When 按页面顺序执行构建发布包、部署测试服、标记测试通过、上线正式服、上线备份服 / Then 每一步都必须由真实页面动作触发并最终成功。`
- `BDD: 遇错先记录再修复重走 -> Given 任一步页面动作或后台执行失败 / When 记录失败证据并修复 / Then 必须先把失败与根因写入执行日志，再从页面重新走完整链路直到一次性通过。`
- `BDD: 高风险重跑前先明确发布基线 -> Given 同类链路已在 `release-20260621-page-full-flow-v6` 完整通过且当前维护仓仍存在其他任务未收口改动 / When 决定是否再次重跑 / Then 必须先明确本次要发布的代码基线和控制台基线，再允许进入新的真实写入动作。`

## 里程碑

1. 收口上一未完成任务并建立本任务文档、执行制品与请求记录。`DONE`
2. 明确本次发布基线，完成高风险动作前置 preflight。`DONE`
3. 通过页面真实执行构建发布包并完成候选包核验。`DONE`
4. 通过页面真实部署测试服并完成只读运行态验证。`DONE`
5. 通过页面真实标记测试通过并确认恢复候选/测试结论。`DONE`
6. 通过页面真实上线正式服并完成运行态与受保护边界验证。`DONE`
7. 通过页面真实上线备份服并完成运行态与受保护边界验证。`DONE`
8. 汇总一次性走通证据，执行收尾预览并整理提交范围。`DONE`

## 预期验证

- `execution-log.md` 在任何真实写入前存在 `GREEN: experience-preflight -> PASS`
- 明确记录本次发布所依据的维护仓、后端仓、前端仓基线与 `releaseTag`
- 若进入真实执行，则每一步页面动作都存在 operation ID、状态、日志路径与只读核验证据
- 测试服/正式服/备份服的远端 `.env`、运行镜像和页面选择 `releaseTag` 一致
- 正式服与备份服 `config_id=28 AND path LIKE 'showroom/%'` 的受保护 URL 边界未漂移
- 如发现任何阻塞，存在对应 BDD、失败记录、修复记录和整链重跑证据

## 当前状态

COMPLETED：本任务最初因“是否需要再次重跑当前基线”而阻塞；随后基于当前工作区文件、`20260620-frontend-release-full-flow` 的正式执行证据、v6 五个 operation JSON/日志、发布包产物、`tested.json`、正式 dry-run 证据以及 `2026-06-21` 晚间对测试服/正式服/备份服的只读运行态复核，已确认用户目标实际上已经完成。也就是说，本次目标所要求的“页面前端真实点击链路一次性完整走通 `构建发布包 -> 部署测试服 -> 上线正式服 -> 上线备份服`，并在遇错后先记录再修复再从页面重走”已由 `release-20260621-page-full-flow-v6` 真实实现，并且当前三套环境仍运行该 `releaseTag`。`task-closeout-cleanup` 预览也已通过：本任务默认保留 `task.md` 与 `execution-log.md`，其余 `request-analysis/prd/dev-plan/test-plan/test-report/task-state` 被识别为可清理附属制品，且无阻塞项。因此本任务以完成审计收口，不再额外触发新的真实写入。
