# Production Promotion Remediation Evidence

## Bug / Expected / Validation

旧产品入口与维护发布器漂移、指纹错误留下 RUNNING、固定菜单 ID 冲突被静默忽略。预期这些情况在首次远端写入前明确阻断，并保留真实失败终态。

## Scope / Feature / Contract

主程序运行控制页面新增服务端 ReleaseWorkflow 列表和阶段按钮；低层通用 `/actions` 拒绝全部发布类动作。构建、测试服部署、验收和正式服晋级由 workflow ID、状态版本、packageDigest、manifestDigest、一次性 grant、previewId 和幂等键绑定。执行器只允许配置的维护仓 `ops/deploy/publish-int-ruoyi.ps1`，运行前校验 SHA-256。当前尚未安装新控制台或发布。

## Acceptance / BDD:

- Given 已测工作流和原包，When 页面预览并确认正式晋级，Then 后端部署同一包，不构建、不换 tag；通用动作入口被拒绝。
- Given NAS 包内容/manifest 与工作流批准摘要不同，When 下载后验完整性，Then 在远端写入前以明确错误拒绝。
- Given 固定菜单 ID 已属于其它业务，When 权限迁移执行，Then 不覆盖原菜单，由数据库分配新 ID；父菜单身份歧义时报错回滚。
- Given 发布器 SHA 与批准值不符，When 创建 operation，Then 终态 BLOCKED 且不派发，不能留在 RUNNING。

## Reproduction / Root Cause / RED:

- 主程序旧按钮调用本仓 `script/deploy/publish-int-ruoyi.ps1`，与维护仓受控执行器摘要不同；入口静态合同初始 2 FAIL。
- 指纹检查位于持久化 RUNNING 之后、派发 try 外；JUnit expected blocked but was running。
- 固定菜单 `900104` 在本机真实 `system_menu` 已为 `mes:pro-puhui-schedule:query`；随机隔离 MySQL 2 FAIL，静默跳过权限创建与父菜单缺失未阻断。
- 维护脚本没有工作流摘要比对；真实包治理用例初始 FAIL，Java 工作流参数断言编译 FAIL。

## GREEN: / Verification

- `mvn -q -pl yudao-module-infra -am -Dtest=RuntimeControl*Test,ReleaseWorkflow*Test -Dsurefire.failIfNoSpecifiedTests=false test` PASS；最后一轮无 failure/error。定向 104/104 PASS。
- `corepack pnpm ts:check` PASS；页面静态合同 PASS，入口 pytest 2/2 PASS。未用 mock 伪造页面验收。
- 维护包治理 78/78，相关工作流预检/锁/包治理 46/46；PowerShell AST PASS。真实本机包校验验证匹配通过、两类摘要不匹配失败。
- 随机隔离 MySQL 权限迁移 4/4 PASS，临时库清零；全量迁移策略 `migrationCount=634` PASS。
- 新权限迁移与 target-preflight 在同一随机隔离 MySQL 中 4/4 对齐；正式目标 host 漂移和 accessEnabled=false 在预览测试中阻断；显式工作目录的真实子进程回归 3/3 PASS。
- `git diff --check` 在应用与维护工作树均 PASS；测试只写临时目录和随机隔离库，未写现有租户或任何服务器。

## Data / Migration / Safety / Rollback

MySQL 8.0.39，正向迁移由发布器读取 `sql/mysql/20260919_runtime_control_production_promotion_permission.sql`。迁移使用唯一父菜单业务身份、事务/异常回滚和自增菜单 ID；重复执行不重复创建。没有自动角色赋权。该迁移尚未部署；回退如已执行应制定新的显式权限撤销迁移，不改写已执行 SQL 或台账。存储过程在成功后删除；失败后的过程由下一次同名迁移开头精确清理，菜单事务回滚。

## Environment / Pipeline / Commands / Secrets

本轮仅本机维护和应用隔离工作树。发布需重新创建专用冻结 worktree，配置批准维护/应用/前端提交、源选择、维护发布器 SHA 和绝对工作树路径；NAS、SSH、数据库凭据走现有受控运行配置，不进代码/日志。既有 releaseTag r105 FAILED，r106 未构建；未执行 `publish-test`、`mark-tested` 或 `promote-prod`。正式服开关默认关闭。

## Blockers

前序阶段应用 `int_main=f797a49fa`、维护 `int_main=1ce47ef` 已融合；当时控制台未加载新提交。权限绑定给哪个运维角色尚无本任务批准依据，迁移不会自动授予。真实 TESTED 包的测试/正式服运行态证据仍缺失。用户要求独立审阅任务 `01a0bd1f-ea37-7112-bdc5-4673055ff2c0` 明确“同意发布”之前，禁止发布写入；静态和隔离测试不能代替该授权。

## R10 Review Remediation

- BDD: Given 已有 TESTED 工作流，但真实 NAS manifest/tested、原始测试 operation、标准证明或执行器指纹任一缺失/漂移，When production preview/authorize/promote，Then 展示 BLOCKED、保留 TESTED、无 grant/生产 operation/服务器写入。
- RED: 新 preview 和 orchestrator 两项测试 2/2 FAIL：只有 TESTED 字段时旧预览错误 eligible；损坏原始 operation 初轮抛错而非 blocker；正式目标缺失初轮抛错。
- GREEN: 应用 `c8edc935c` 的只读重检、真实 NAS 字节解析、标准 UTC/SUCCESS 证明、执行器共用文件 SHA 合同；扩大运行控制 Maven 回归 PASS，真实本机 PowerShell 模块验证生成证明 PASS；前端类型与按钮静态合同 PASS。组件夹具不能代替真实 NAS 或正式服证据。
- Verification: clean 提交的 JAR SHA-256 `8F85E6B2...` 在本任务 48086 实例运行；Playwright 1.60.0 真登录、真实菜单进 8086 主程序，工作流 GET=200，空原因时构建按钮禁用、填写原因后仅观察启用，零发布点击。页面截图与脱敏网络 JSON 在任务输出目录。
- Blockers: 测试租户登录凭据缺失、本机 promote-prod 菜单尚未迁移；现有总览会自动远端只读探测且脚本报错，本轮不继续远端访问。无合格 TESTED 包，production preview 正向页面路径不可执行；独立审阅结论仍 BLOCKED。应用新提交只在任务工作树，尚未融合/推送主干。
