# 自动链按阶段选择已安装控制代次

## Current Status
ready_for_review — 2026-11-07 21:34:20 UTC冻结，47项本机合同通过，实际旧FULL与0d安装5份原件SHA保持。未创建真实阶段选择，未执行实际浏览器/服务器/安装或工作仓Git写入。

## 目标与里程碑
FULL373已在0d445782dc06995b3c84b1b45146ea4b75483f92代次真实完成，原提交/终态/审计/源恢复证明须保持历史身份。I1/I2可能采用随后修复的source控制包，Spug11个运行文件仍保持原0d代码。需要每阶段明确选择、分别证明来源包和Spug输入，不能以所有提交强制相等阻止合法独立升级，也不能按latest自动串用代次。
- M1：与source-only安装负责人冻结新public/private报告及阶段选择schema，父任务审阅范围。
- M2：先BDD/RED覆盖旧FULL历史、I1/I2新源+原Spug、pins错绑、未安装/源提交漂移/Spug漂移。
- M3：最小修改本TASK UI/preflight helper及专属测试，运行真实本机文件/Git合同；不启动真实UI或调用服务器。

## 定位事实
- prepare_automatic_ui_preflight.py主入口固定读取PRIVATE/automatic-control-installation-57.private.json，并从同sourceCommit推断Spug报告；要求source/build/Spug同commit。
- verify_deployment_inputs将backup_engine/recovery/包files.json和Spug运行输入合并后，用单一installedCommit比较HEAD/index/worktree，无法容纳source-only升级。
- automatic_incremental_ui_acceptance.cjs的gate检查只绑定单implementation/installation/build commit；新receipt没有独立source与Spug代次pins。FULL原receipt必须不改写。
- verify_automatic_backup_chain已有显式--installation但默认旧回执；verify_automatic_source_restoration、closeout_contracts存在固定0d/全链共源安装假设，已通知其负责人。它们不在本次UI/preflight直接修改范围。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否；没有选择或报告不PASS即失败，不按latest、文件存在顺序或commit前缀猜代次。
- 是否从根因和长期维护角度解决：是；提交/执行阶段绑定不可变已安装代次，来源和Spug分别验证精确Git输入及实际文件pins。
- 是否存在临时补丁或绕过：否；FULL原0d凭据和package保持；新选择仅允许已明确安装和验证的新source包，不能跳过Spug11核验。

## 经验门禁
Trigger：同一真实自动链跨控制组件升级。Preflight check：每阶段明确source public/private安装pin、build pin、Spug原安装pin；新来源已实际激活；两组Git输入分别与准确安装commit比较；receipt与选择相符。Blocker：原FULL证明漂移、未安装/错阶段/错source、new source实际文件不符、Spug11变更、HEAD/index/worktree任一部署输入改变。Verification：本机文件/Git合同RED→GREEN，原历史文件SHA保持；实际远端/UI由父任务另行执行。Forbidden action：覆盖0d回执、共用单一commit伪装独立部署、自动选择最新报告、按未知结果重提POST。Evidence：本方案、安装负责人冻结合同和后续专属测试记录。

## 拟议BDD（合同冻结后细化）
- Given FULL原submission绑定0d；When历史verify/audit读取FULL阶段选择；Then仍引用0d，保持原所有proof字节。
- Given I1明确选择新source包、原0d Spug；When两组HEAD/index/worktree及实际安装文件均匹配；Then可生成分别标记两代次的新gate；不要求两commit相等。
- Given source输入变更而Spug未变，或Spug11任意文件漂移；When预检；Then分别以对应部署输入错误阻止gate，不能互相掩盖。
- Given未受理/未知结果UI规则；When加入代次信息；Then仍wx保存原请求并且最多一次POST，verify只沿原编号GET。
- Given选择pins与receipt/阶段不符、报告仅PREPARED或不PASS；When任何阶段使用；Thenfail fast，不读取默认latest代次。

## 已冻结合同与改动边界
archive新public报告AutomaticSourceControlUpgrade/v1，文件automatic-source-control-installation-<commit7>.json，PRIVATE同stem.private.json；controllers固定[0]SOURCE、[1]保留MAIN_TARGET。controllerGenerations逐项role/sourceCommit/fileManifestSha256/fileCount/packageSha256/buildPin，MAIN_TARGET另installationPin原57报告。顶层source身份、包、policy/epoch保留，实际安装仍需PASS；新报告不覆盖原0d。
每阶段固定automatic-<full|i1|i2>-deployment-selection.json，schema AutomaticStageDeployment/v1，kind/sourceConfigRef/sourceCommit/spugCommit/sourceInstallationPin/sourcePrivateInstallationPin/sourceBuildPin/spugInstallationPin；pin均file/bytes/sha256，private只引用文件名和摘要，不嵌私密配置。纯load_stage_deployment(task,private,kind)统一校验，供archive/epoch明确采用；不存在选择即拒绝。
FULL旧0d报告仅精确旧文件名+完整commit+真实原pins兼容，normalize为两个同代控制；新source-only报告必须明确schema，不能以字段缺失推定旧版。Spug固定既有0d的11文件清单和安装pin，每阶段仍独立验证其Git输入与运行SHA。
新增本TASK automatic_stage_deployment.py及专属测试；修改prepare_automatic_ui_preflight.py、automatic_incremental_ui_acceptance.cjs及专属测试/说明。旧proof不改写，audit/source-restoration/closeout由各自负责人处理。
gate和新I1/I2 receipt为v2，implementationCommit继续表示source实际commit，独立spugCommit/deploymentSelectionPin绑定选择；verify必须同原receipt代次。旧FULL v1只接受kind FULL和原0d，且显式FULL选择也指向0d；保持原receipt字节不变。旧v1未知代次不得兼容。unknown仍仅GET原id，最多1POST不变。

## 精确测试场景
- 真实临时文件：原FULL0d显式选择通过且原文件SHA不变；I1新source/旧target/原Spug通过；private/public错pin、unknown schema、未PASS、Spug文件数/名单变动、kind错绑、缺selection拒绝。
- 真实临时Git仓：新source commit与旧Spug commit可分别通过精确闭合scope；HEAD/index/worktree source或Spug修改各自失败；其它catalogue/task记录变化不阻塞。只创建隔离测试仓，不改真实main/task索引或refs。
- Node VM纯合同：不运行main/浏览器，v2gate完整选择匹配、v1历史FULL限定、错阶段/错commit/选择漂移拒绝；原真实FULLreceipt pin保持。

## RED → GREEN → REGRESSION
- RED：新stage纯loader首次pytest收集失败ModuleNotFoundError；实现后12项文件合同PASS，补前代PID/epoch与严格public/private绑定后14项PASS。
- RED：source/Spug分scope新增7项真实临时Git测试在旧接口ImportError，随后独立component/source+spug实现，完整27项真实临时Git历史/index/worktree合同PASS。测试只在pytest临时仓创建提交，不改主线/任务仓index或refs。
- RED：Node VM新阶段合同原3项因函数缺失失败，1项拒绝类测试当时只表达预期失败；实现明确合同后4项全部PASS，原2项登录纯合同保持PASS。VM不执行main、不打开浏览器、不读取账号。
- GREEN真实本机旧报告：将实际旧0d public/private/build/Spug报告复制到自动清理的临时文件夹，构造该临时夹的FULL选择，loader校验PASS/11文件；真实TASK没有产生stage选择文件，原报告未改写。
- REGRESSION：automatic-stage-deployment-regression.json及.txt固定41 Python+6 Node=47 PASS，语法通过，源6文件SHA受测前后相同；原0d source/Spug及FULLsubmission/terminal/audit共5份SHA保持。FULL source-restoration尚未存在于该回归快照，不伪造已验证。
- HANDOFF：调用合同见automatic-stage-deployment-usage.md；archive消费统一loader与acceptance/current选择v2，epoch负责audit/sourceproof逐阶段适配。实际安装/选择/预检/UI由父任务完成。
