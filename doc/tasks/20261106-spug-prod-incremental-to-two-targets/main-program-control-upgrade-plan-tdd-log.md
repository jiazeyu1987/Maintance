# 控制代次升级纯规划重构证据

## Current Status

ready_for_closeout。本阶段纯planner实现及必要本机验证完成并冻结：26项GREEN、原路由合同39项GREEN，零skip；等待父统一审阅/提交/实际新代流程。前一publication工作已完成本机148/125验证并冻结交父，尚未冒称完整现场发布完成。本阶段只新增纯planner、其测试及本记录；没有新增或执行PRIVATE wrapper，没有写实际r5计划，没有安装/服务器/Docker/构建/提交。

## 目标、里程碑与预期验证

从已核前代配置图与四份真实控制core派生新代：35项完整闭包，8项新建、27项原pin保留。仅重绑定engine程序工具、三owner formalModuleDirectory、四control程序pins/PYTHONPATH和repo/owner引用；保持数据、epoch、认证、31原执行路由、来源/目标保护、12selector语义。新公开/私有v2显式绑定commit/revision/build和前代。

里程碑：读取父设计/前代结构 → 协调bundle/API与输出schema → 新失败测试实际RED → 最小实现GREEN → 旧合同/精确保全回归 → 冻结交父。只运行本机纯函数/临时文件，不执行真实r5规划器，不写真实r5计划，不安装或生成虚假成功。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。未知engine路径、旧pin/构建无法精确定位、组不闭合、任一非批准变化均拒绝。
- 是否从根因和长期维护角度解决：是。独立纯可复用planner，显式前代bundle及新commit/revision/build，不exec/编辑/替换r4源码。
- 是否存在临时补丁或绕过：否。不改原件，不用旧staged settings冒充live，不绕过前代验证或安装准入。

## 经验门禁

- Trigger：已安装控制服务的新代配置规划。
- Preflight check：核父设计、已核前代四控制/35文档/原receipt链，使用显式新构建manifest和前代pins；原settings/history/epoch/保护值完整保持；读docs/experience-index.md命中的release-agent-checklist活动回执历史保全、包清单身份、自动增量周期门禁。
- Blocker：前代不闭合、当前/新构建未知、任意外部程序pin或engine路径无法证明、文档别名/重复、分组或settings不精确、原件漂移。
- Verification：先实际RED→GREEN，再真实临时文件变动拒绝、8/27闭包与旧规划保全合同回归；父单独真实构建/安装/HTTP/UI验收。
- Forbidden action：不访问服务器/Docker、不构建/提交、不执行wrapper、不写实际r5计划、不改generation/custody/activation/publication/selection/observe/旧r4或共享日志。
- Evidence：本专属记录、独占PRIVATE测试日志、父control-generation-upgrade-plan及refactor-design；PowerShell/Python显式UTF-8，不使用缺失E盘资料替代风险动作授权。

## BDD（实施前）

- Given 显式新commit/revision/build及已核前代bundle，When 纯规划，Then 只返回候选公开/私有v2，无文件写入且输入原值不变。
- Given 前代35文档及四控制闭合，When 拓扑派生，Then 恰8新/27 retained互斥并完整覆盖35项，保留项路径/pin/value原样。
- Given 来源repository、三owner、四control的新engine程序已在新包manifest，When 重绑定，Then 仅批准字段变化；数据限额、epoch、来源/目标、认证、外部工具及其它环境不变。
- Given 原31sourceConnections及四目录/目标连接，When 派生新代，Then 原执行route/凭据/旧文件与历史指纹不变，新四连接使用本代独占名，selection三来源映射与target作用域保持。
- Given 任一缺件/错pin/非包成员/外部engine路径/重复或重叠文档/非法revision/同代commit，When 规划，Then 明确拒绝，不扫描最新、不猜路径、不写候选输出。
- Given 旧r4真实字节，When 运行纯合同回归，Then 原件SHA及原planner既有验证结论不变，不exec旧模板。

## 接口冻结与 RED

generation owner已冻结bundle键：generationPin/generation/build/plan/privatePlan/controllersByHost/selections/inputPins/targets/sourceBaseline/custodyByHost；selections为真实控制-only选择形状，不含伪装完整安装字段。planner只消费该已核bundle，同时再次交叉核配置图/实际core与程序成员。

父明确要求两代实际standard包147成员raw bytes作为显式输入，逐成员计算SHA/字节及manifest；独立 ArchiveCataloguePackageDelta/v2 报告pin/raw绑定唯一已审语义变更。实际28个raw变化含27纯CRLF与唯一control/recovery_control_restore_catalogue.py语义变化；不得把换行漂移当程序修改，也不允许额外语义变化。函数输入为显式source_commit/revision_id、build_document={pin,raw}、package_delta_document={pin,raw}、package_files/previous_package_files、predecessor、private_plan_path和observed_at；纯返回{privatePlan,plan}，不读写文件或执行任何wrapper。

v2保留原计划投影字段并新增revisionId/predecessorGenerationPin/previousPlanPin/buildPin/packageDeltaPin；完整documentsByHost仍35，newDocumentsByHost/retainedDocumentsByHost在private含pin+value，在public只含pin。新engine为原root下engine-main-program-<newshort>；configuration目录main-program-<newshort>-<revision>，四连接文件同样显式short+revision。当前privatePlanPin纯计算canonical私有候选及显式唯一PRIVATE输出路径；真正独占写入/路径别名检查属父后续入口，当前不执行。

RED: `python -X utf8 -B -m pytest -q --tb=short -p no:cacheprovider TASK/test_main_program_control_upgrade_plan.py --basetemp PRIVATE/main-program-control-upgrade-plan-red-r1` -> exit2，collection 1 ERROR，ModuleNotFoundError main_program_control_upgrade_plan，零skip，1.85s。独占日志1214B SHA256 `3797bcf2bf98d43745e8c9988ab3d679396120272b3664275c0ad7734c6703fa`。此前未创建实现；测试原件为真实两代包/构建/delta/r4/四core，generation索引为明确外部已核bundle协议seam，不冒充真实索引或新安装成功。

首轮GREEN-r1实际exit1，3FAIL/21PASS，0.71s；唯一正向共同错误是严格私有顶级名单漏列原有sourceRegistrationSelectors，未读取秘密或改变原件。4439B原日志SHA256 `4ccf1ebb8eb0d94ca209fd141fd2a637f2d83f219b3670e334fd2863af32a41f`。精确补原字段后GREEN-r2实际exit0，24PASS，6.73s，零skip；101B日志SHA256 `3349438f91e995ce4d874cd1afc0127604ae798b70f1734c220e658bf003a3e8`，均PRIVATE独占main-program-control-upgrade-plan-green-r1/r2.log。

与generation owner进一步冻结：输出名必须同时含commit短码与revision，即公开main-program-configuration-plan-<newshort>-<revision>.json、私有同stem.private.json，避免不同commit复用r5；原r4固定文件不动。未运行wrapper或写真实候选文件。

## 调用方已加载计划的正式校验：事前BDD

父已批准 `validate_control_upgrade_plan(public,private,**已核材料)` 纯入口。它使用同一planner重建并逐对象全等，不复制宽松规则；observed_at与输出private唯一路径由调用方从已读public显式传递，继续核格式/边界。两项合同：Given 完整相同已核材料及其候选public/private，When 校验，Then 返回相同候选；Given public分组或private数据任一改变，When 校验，Then 明确拒绝而不生成输出。先独立两项RED再实现。

实际validator RED：同前命令加 `-k validator --basetemp PRIVATE/main-program-control-upgrade-plan-validation-red-r1`，exit1，2FAIL/24deselected，3.19s，零skip；两失败精确为未实现validate_control_upgrade_plan属性。1574B日志SHA256 `22875050145db4be392787b46b9f56c4059e453315a18f468814f1919688be1c`，PRIVATE独占保存。

## 最终 GREEN、旧合同回归与交接

最小validator仅调用同一planner重建，并对private/public逐对象严格相等；不另写可漂移规则。完整GREEN-r3：`python -X utf8 -B -m pytest -q --tb=short -p no:cacheprovider TASK/test_main_program_control_upgrade_plan.py --basetemp PRIVATE/main-program-control-upgrade-plan-green-r3`，实际exit0、26PASS、11.00s、零skip；102B日志SHA256 `13ea83d37cb34ccf9deb2000b94e0bfee9dc3c025d7df2b0d2a4825943057880`。

固定旧路由REGRESSION-r1：同前Python/环境，`-X utf8 -B -m pytest -q --tb=short -p no:cacheprovider ops/spug/test_smallapp_source_rotation.py ops/spug/test_smallapp_cross_route.py ops/spug/test_smallapp_safety.py --basetemp PRIVATE/main-program-control-upgrade-plan-route-regression-r1`，实际exit0、39PASS、46.16s、零skip；102B日志SHA256 `83528d81277b0c4e72c1b71787f697ae77bdf94f2b17c5fc6106c78433eee590`。

所有日志独占PRIVATE，不覆盖首轮失败。PYTHONPATH明确PRIVATE/test-dependencies、TASK、REPO/ops/spug、REPO/ops/recovery；PYTHONDONTWRITEBYTECODE=1、PYTEST_DISABLE_PLUGIN_AUTOLOAD=1，禁cacheprovider，basetemp各自专属。原TASK/test_main_program_route_plan.py会importlib.exec_module执行r4模板，按父本阶段明确“不exec r4”未运行；旧规划合同由26组内 `test_old_planner_preservation_contracts_still_accept_original_r4` 只读真实r4并直接调用原validate_history_routes/validate_settings/validate_selection_routes，三项实际通过且原r4/四core/构建/delta原字节结束复核保持。这里没有声称旧模板测试或整个旧包测试已重跑。

冻结API：

```python
plan_control_upgrade(*, source_commit, revision_id, build_document,
    package_delta_document, package_files, previous_package_files, predecessor,
    private_plan_path, observed_at) -> {"privatePlan": private, "plan": public}
validate_control_upgrade_plan(public, private, **materials) -> 同上候选
```

build_document/package_delta_document严格{pin:{file,bytes,sha256},raw:bytes}；两代package_files为标准包147个相对成员到真实raw bytes的字典，不含package.json；predecessor必须来自正式generation reader已核bundle。新build和delta raw pin、两代manifest/成员集合/每成员SHA/bytes及所有Python AST实际核验，raw delta/纯CRLF/唯一已审语义文件与delta报告逐项匹配；不代替实际tar完整包SHA、clean-worktree/Git和上位generation原件验证，调用方仍需完成这些读取门禁。

public v2完整字段为原r4投影所有字段，并新增schemaVersion、revisionId、predecessorGenerationPin、previousPlanPin、buildPin、packageDeltaPin、newDocumentsByHost、retainedDocumentsByHost。private v2完整字段为原v1顶级集合（保留status、sourceRegistrationSelectors等），新增同7个代次/分组字段，schemaVersion换v2；不把public observedAt新增到private。两组private含pin/value、public只pin；documentsByHost严格[*new,*retained]。控制/owner前代pins取actual cores而非r4安装前currentSelections。currentSelections使用bundle.selections，显式control-only前代。

configuration目录main-program-<short>-<revision>，engine同root的engine-main-program-<short>；四connection本代short+revision独占名，值与旧四份全等；原31sourceConnections/全部非本代target routes/selection作用域、settings与12selector原登记SHA、sources/targets/epoch/保护/原任务严格保留。8项新pin按canonical值计算，27项原path/pin/value完整保持，未调用任何stager或写文件。

父后续必须从实际generation原件读取bundle，独立核两实际tar/报告完整SHA并提取成员，将其传纯函数；对显式PRIVATE目标做真实别名/存在性/O_EXCL与原字节读回，随后另写实际unit/environment/stage/coverage并完成新代activation v4。只有实际四控制/原历史保全/认证目录/Spug发布及UI通过才能完成整个目标，本机候选不能替代它。
