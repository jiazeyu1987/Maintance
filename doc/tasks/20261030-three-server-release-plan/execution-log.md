# 执行记录

- 用户需求：将“最新代码发布到三服”的拟执行方案写成文档；本轮不授权实际发布。
- 已执行唯一只读 UTF-8 bootstrap：适用 AGENTS.md、上一任务状态、docs/experience-index.md、E:\IntRuoyi\docs\powershell-memory.md（固定旧路径缺失，后续核对已导入仓库对应文档）。
- 已识别上一同链任务 20261030-spug-handoff-install 为 completed；本任务继承 PASS_WITH_FINDINGS 中的发布前阻塞项。
- BDD: 文档交付 -> Given 仅要求方案 / When 核对现有发布契约并写文档 / Then 不构建、不发布、不更改远端或业务数据。

## 2026-10-31 编写与验证

- 已按经验索引读取维护仓发布 checklist、不可变包/摘要绑定、已执行迁移不可变、结构演练/目标只读预检、真实登录和 staging 证据门禁；摘取到 task.md。未全量阅读无关经验。
- 旧 E:\IntRuoyi 路径缺失；改为核对已导入、固定 f3ee14997e4dd0174f8bee68f3cde561690a7f8b 的 IntRuoyiAll/docs 正式规则，记录该来源，未伪造旧路径存在。
- 核对 b4feadcfdc17e57a4d2d829093963339637a80b8 维护代码 README、intruoyi_executor.py、intruoyi_build.py、release_precheck.py 和 UI；确认测试直发、正式完整数据演练、正式/审查技术与业务验收分离、恢复和补发语义。泛用旧流程不与当前 Spug 入口混用。
- 只读 Git 检查证实 IntRuoyiAll/Backend/Fronted 的 show-toplevel 均为同一根仓库；方案采用本机实际拓扑。
- 只读核对 start-local.ps1：普通脚本要求 SourceStopped，引用已审核 portable/start.ps1 和稳定安装根目录；文档命令未执行。
- 安装验收 PASS_WITH_FINDINGS 原样继承；.env 契约漂移、网络持久性/演练网段、静态迁移计划不能替代实际演练均列为未来发布前处理事项。
- GREEN: documentation-verification -> PASS。verification.json 共 11 项检查全部为 true，文档 163 行，SHA-256 为 3d07c4b79d120093de1300e36bd6cd2eb1d0ec0ea5896b6df2345f7f6a66dd31。
- GREEN: git diff --check -> PASS（仅存在仓库既有 core.autocrlf 提示，无格式错误）。纯文档未做运行测试，未将静态核对描述为真实发布验收。
- 更新 docs/request-command-log.md 并 UTF-8 回读验证；该共享文件原有他人/用户修改，保留在工作区，不整体暂存。
- 收口前状态：ready_for_closeout；本任务未创建 worktree、未产生实现代码、未启动/停止进程或更改控制台，远端/发布动作均为 0。

## 收口

- 交付物单独提交：6594c8c `文档: 明确最新代码三服发布与验收方案`，仅含 release-plan.md。
- GREEN: closeout -> PASS。本任务 worktree 创建/删除数均为 0、无实现新提交需融合、运行控制台未改动，无恢复动作；其他任务资源未操作。
- 最终状态 completed 仅指方案交付。真实发布未授权/未执行，现有发布前阻塞原样保留。
- 最终任务记录与脱敏 verification.json 单独提交；docs/request-command-log.md 共享修改继续保留，未推送任何提交。
