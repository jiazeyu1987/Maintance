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

## 2026-10-31 用户审阅修订（进行中）

- 原方案 completed 后按新审阅重开文档修订；七点修正及 NAS 原包重传纳入任务。原方案将 static-only 视为可能需要扩展开发的依据，且对无效 .env、网络彻底治理、自动融合和只读回归表述过度，现按最新明确范围纠正。
- 新增明确要求：本地来源已保存 GxP 模式为关闭，原包清单及三服部署后实际模式全部为关闭；当前不发布，不改模式，仅作必要只读核对。
- BDD: 审阅修订 -> Given 用户明确主流程及边界 / When 对照真实代码修订 / Then 移除无依据新增门槛，补齐 GxP 和原包重传，明确真实验收范围，且无发布或远端变更。
- BDD: GxP 关闭一致性 -> Given 配置来源真实可登录且保存关闭 / When 构建与部署 / Then manifest 和每个目标的实际模式为关闭；当前只读核对来源，不把待执行三服验收记录为通过。
- 本轮无行为代码变更，不新增 TDD 实现测试；编码、文档及代码合同核对照常执行。
- GREEN: experience-preflight -> PASS（仅本地只读 GxP 核验）。配置来源确认为 http://127.0.0.1:8081；TCP 可达，真实浏览器工具与私密凭据文件存在；按现有登录器/页面组件定位真实租户登录、已保存与运行模式。仅允许实际登录 POST，其他业务写请求阻断并报告；不点击保存、不改开关、不重启。截图留仓库外 private/acceptance，仅脱敏结果进任务目录。
- 第一次浏览器核验真实登录及 GxP 保存/运行关闭均已读到，但访问首页触发 `/workbench/context` POST，被只读保护拦截，因此脚本整体 FAIL。保留 local-gxp-verification.attempt1.json，不把它写为整体通过；不放开不需要的请求。核对 LoginForm.vue 既有 redirect 参数后，改为真实登录直接进入配置页面，再检验同一 GxP 条件。
- 第二次直达配置页仍有 2 次自动 workbench/context POST 被保护拦截，严格脚本整体仍 FAIL；保留 local-gxp-verification.attempt2.json。两次均实际读到保存/运行 DEVELOPMENT_DISABLED、auditEnabled=false、无待重启、页面保存与运行均显示关闭；故停止重复浏览器运行，不扩大成工作台修复。
- SCOPED PASS: local GxP saved/running closed -> 八项实测事实成立，私密截图存在。local-gxp-verification.json 保存事实、原始 attempt2 路径与 SHA、browserHarnessStatus=FAIL 及拦截记录；仅 GxP 验收 PASS，不将其改写为完整 E2E 通过。原始两份 FAIL 不修改。
- 已逐项修订方案：static-only 作为现有设计；.env 按是否生效判断；路由按用户已持久修复记录且不重启/删除现用演练；补齐本地来源→manifest→隔离→三服保存/运行关闭；只读与真实测试租户写入回归分开；按范围决定 Git/清理，不自动 int_main 合并；NAS 封包上传失败通过原 resolve-task retry 校验重传，不重新编译。
- README 与 nas_package_retry.py/UI 已核对重传前提：原步骤 publish-original-package-to-nas、原任务未决且无部署影响、原 SHA/releaseTag/manifest/归档全部成员验证、同包双摘要不变；NAS complete/partial 冲突拒绝覆盖。本文未实际访问 NAS 或执行重传。
- 方案内附“给另一台电脑的审阅反馈”，可随资源交接传阅；本轮未通过任何工具向另一台电脑/会话发送消息。
- GREEN: documentation-review-verification -> PASS。verification.review.json 所有静态/来源/敏感值检查通过；方案 188 行，SHA-256=7233967c1923313cb23c87e38cd53e781f2c4fa40a839b753ced1b1493e5584a。此 PASS 指文档核对，不改写 browserHarnessStatus=FAIL，也不表示三服部署验收通过。
- GREEN: git diff --check / node --check -> PASS。保留原工作区修改和空暂存区；按用户本次范围不自动提交/推送/合并/清理，无任务 worktree 或控制台需恢复。
- 修订收口 completed：文档更新和本地 GxP 关闭事实核验完成；三服发布、NAS 重传及部署后模式核验均未执行。
