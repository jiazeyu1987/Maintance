# 当前安装证明消费者接入：TDD 记录

## Current Status

ready_for_closeout。本机实现、RED→GREEN→REGRESSION及历史冻结检查完成，源/测试冻结，交父审阅与实际新 acceptance 消费。父任务已批准 `spug-current-installation-consumers-design.md`（14443B，SHA256 `edefe67e0a29254c8d4e96c9595780fa5daee9b9868e37761a9ac98160a41159`）。仅本机实现独立 dispatcher 与三个明确消费者接缝；没有访问服务器、浏览器，没有执行安装/备份/恢复/构建/提交。父已实际完成 r7 generation；本子阶段验证时仍无新 completed acceptance，合同测试不代表现场安装/页面/备份验收。

## 目标与里程碑

1. RED：新模块缺失、有限 schema 分派和消费者读取合同先失败，原历史失败保持。
2. GREEN：完整正式 loader 验真后派生统一只读视图；新 acceptance 保留真实 schema/pin。
3. REGRESSION：原消费者及受影响本机合同通过，历史五 reader/selector/原件 SHA 保持；记录原始日志和最终修改 SHA。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。仅精确 pinned schema 分派，未知拒绝。
- 是否从根因和长期维护角度解决：是。安装证明来源显式分离，消费者使用同一经完整原件校验的投影。
- 是否存在临时补丁或绕过：否。旧历史 reader 不改；包目录由正式 build pin 解析，不猜文件名或短提交目录。

## 经验门禁

- Trigger：Spug 运行依赖闭包、控制升级后原安装证据保持及当前 UI/链审计接线。
- Preflight check：已核五个历史 attempt 的完整 inputPins 和递归 pin 对象；拟改三个消费者均未绑定，旧 selector 与五 reader 冻结。先确认新 loader 完整原 native 闭包及明确 selector。
- Blocker：旧原件漂移、缺少正式 acceptance、仅信自述 PASS、猜 latest/build 目录、未知 schema 或读取未绑定原件。
- Verification：RED→GREEN→REGRESSION 原始本机日志、全部输入复验、旧文件 SHA 保持。
- Forbidden action：不得改历史 reader/custody/selector，不得输出私有 settings/凭据，不得以协议 fixture 声称现场成功。
- Evidence：已批准设计中的五 attempt SHA 表与源文件冻结身份；本日志记录后续实际结果。

## BDD

- Given 原五字段 v4 selector，When 精确 inputs schema 分派，Then 旧 v1/v2 仍调用原 validator，新 acceptance 调其正式 completed loader；缺失/未知字段与 schema fail fast。
- Given 已验证 acceptance 闭包，When 取资源/运行态，Then 565 resourceBuildPin 来自 transitionInputs，guard 来自本次末尾 spug-guard-after，七配置为原已发布值。
- Given 错 result/inputs/generation/build/stage pin 或闭包外路径，When 读取，Then 在任何远端操作前拒绝；不得 fallback。
- Given 公共 CLI，When 验证成功，Then 仅输出安全身份摘要及完整输入 pins；失败为非零，私有 payload 不进入 stdout。
- Given 三个消费者，When 接入新 dispatcher，Then 原实际 UI/source/链/147 文件/读回/epoch 门禁保持，正式包目录从 build pin 得到。
- Given 五个历史 attempt，When 本轮结束复验，Then 原 reader/selector/原件保持逐字节一致。

## 实际执行

RED：`test_main_program_current_installation.py` 实际 29 FAIL / 0 skip，26.46s，exit1。28项缺新模块，1项实际 MAIN 包入口缺 `build_pin`；真实旧 history fixture 成功建立，无setup错误。原日志 `spug-current-installation-consumers-red-r1.log`。

RED：`node --test test_current_installation_cli.cjs` 实际12 FAIL，exit1，缺正式 `readAuditBoundInput`/CLI 消费入口。原日志 `spug-current-installation-cli-red-r1.log`。CLI 正向测试仅 subprocess 输出协议边界，不是伪造现场 completed acceptance；真实 loader 拒绝薄 PASS 回执另有直接测试。

第一次 GREEN 实际 25 PASS / 4 FAIL，原日志 `spug-current-installation-consumers-green-r1.log` 保留，不能算通过：完整已验 native 闭包包含正常的 0B stderr，raw file pin 错误要求大于0。改为明确非负整数（JSON仍必须正式解析）；新 projection 测试还须显式纳入真实历史 custody 自身 pin，不能把旧 verifier 不返回的额外 pin 假称已在其闭包。两处修正后实际29 PASS/34.44s，日志 `spug-current-installation-consumers-green-r2.log`。

第一次相邻回归：Python31 PASS / 1 FAIL，旧r6现场positive被原 `validate_publication_v4` 的 `MAIN_SPUG_ORIGINAL_BYTES_CHANGED` 拒绝；新测试直接比较原调用与新分派同类型同错误，生产旧路径保持。父明确批准把该旧positive测试改为chain消费边界：经真实historical custody正式验真取得旧bundle，单元替换dispatcher结果，保留原v3 parent/147/全部部署字段断言，不声称当前现场prepare成功。CJS原47项14 PASS / 33 FAIL，原AST载体未提供新CLI；父批准仅为该临时协议fixture加固定subprocess摘要边界，保留原所有point/链/页面/矩阵断言。修改前完整五attempt递归pin扫描证明这些相邻测试均零命中。

最终 GREEN/REGRESSION：

- Python：`python -B -X utf8 -m pytest test_main_program_current_installation.py test_main_program_ui_preflight.py test_automatic_main_chain_audit.py -q -p no:cacheprovider --tb=short`，61 PASS，53.95s，exit0，0skip；全部8个归属源码/测试before/after SHA相同。
- JavaScript：`node --test test_main_new_point_ui_binding.cjs test_goal_ui_audit_binding.cjs test_current_installation_cli.cjs`，59 PASS，exit0，0skip；包含固定原页面/矩阵AST不变断言。
- Python5文件内存compile、`node --check verify_goal_readonly.cjs`、限定范围 `git diff --check` 均exit0；没有生成字节码或构建包。
- 五原attempt字节SHA、五冻结reader字节SHA、旧selector与HEAD原字节全部保持；修改源码/测试在五attempt递归pin内均零命中。正式报告为 `spug-current-installation-historical-preservation-r2.json`。r1临时采证命令的输出语句误缩进进循环，仅写出第一条scan后第二次独占写报FileExistsError；r1原件保留但**不得作为保全通过证据**，r2显式绑定被拒r1并断言五条齐全后一次写入。

## 最终实现范围与接口

- 新 `main_program_current_installation.load_current_installation(task, private, *, selection_file)`：精确v4五字段和pinned inputs schema分派；原v1/v2仍原完整validator，新acceptance必须正式completed loader全native闭包通过；原件结束重验。
- `spugRuntime`只在私有内存含本次guard与565build。七原已发布配置由历史c1的已固定privatePlan派生canonical pins并与本次guard完全比较，不发布r7拟新文件名。
- 公开CLI：固定 `python -B -X utf8 main_program_current_installation.py --selection <显式文件> --public-summary`；只输出安全身份/摘要/完整inputPins，失败非零且stderr仅固定错误，不泄漏私有内容。CJS使用固定Python和参数数组、shell=false，实际重验全部闭包文件并纳入结束屏障。
- UI预检保留原真实SPUG_SCRIPT及source健康/epoch/锁/容量/计划；新增结束原件屏障。
- MAIN链审计保留原147成员SHA、native/父链/manifest/readback/epoch/source恢复验真。当前入口始终传明确generation.buildPin；新包位置从原buildCommand的唯一output目录和variants.standard.packagePin精确解析，实际b5fa4c5包目录完整读回147项通过。旧独立package函数默认协议不改。
- 修改三个消费者及父授权的两个相邻测试载体；新dispatcher、Python29测试、CLI12测试。没有改历史五reader、installation_selection、historical custody或原attempt。

## 精确验证原件

| 文件 | bytes | SHA256 |
| --- | ---: | --- |
| spug-current-installation-consumers-red-r1.log | 33149 | `4c0a6bcfa25428ba0f698e1e480667417a89c3ae70c22bf3de6c4b0dc76c9fed` |
| spug-current-installation-cli-red-r1.log | 17441 | `6a80263b04abb173fd8894437ddd501026aad038fe6d475362b58868bc0fc1b3` |
| spug-current-installation-consumers-green-r1.log（FAIL保留） | 3871 | `5573bc3f65bde266925e90995d151385bcc7ad1ed0ec55fab57e3b4191678e85` |
| spug-current-installation-consumers-green-r2.log | 102 | `6a00c49e218184e3dacb952e9de40b37eab15f7a7ae738e5345af36a8ce74fc0` |
| spug-current-installation-python-regression-r1.log（FAIL保留） | 3269 | `9e5d1fa689693c8a86b3a09ae3f99209190cb354cf85edb5686b7c121c4b1f00` |
| spug-current-installation-js-regression-r1.log（FAIL保留） | 63348 | `d4612d117e293333cbf12b26e4f6d4fa83f14f217ff7b22f046b17f904c340d7` |
| spug-current-installation-python-final-r3.log | 102 | `8df2a9947d4d82c667f91a218c4534f8c76b96d4a714aeb8c66df505cb720b01` |
| spug-current-installation-js-regression-r2.log | 4368 | `a758866b2d70506334ed6208afc87f798828dedb73a6e9e18e54efe82153ebf9` |
| spug-current-installation-consumers-validation-r3.json | 2860 | `c0100b59ab8514bcb6453f88105c848d78121ad654a0bcc57789a1e9214a2393` |
| spug-current-installation-historical-preservation-r2.json | 4540 | `487284f8ed22a265df079bdb8bb4c8460fe1a635bcdb027203a36fba1f95d0fc` |

## 冻结实现与测试

| 文件 | bytes | SHA256 |
| --- | ---: | --- |
| main_program_current_installation.py | 11142 | `7a4cbfef68841d2a842ecbd6c96ad99524d9d22ccd3cffbe1cb99eb37682161a` |
| prepare_main_program_ui_preflight.py | 15757 | `53ba5b2de1febb1591db9df635e1c9230c4d419b32d07fc5c9824fefe095f4d7` |
| verify_automatic_backup_chain.py | 18764 | `f5630403a9e0f9eb99ffda704ead3bba876bd9588f1f326b0b05b0d1260e5819` |
| verify_goal_readonly.cjs | 27682 | `2b55821683ddade68c823eaf400287d4945c495f2f3dc7cb7528c3c6004ed3c9` |
| test_main_program_current_installation.py | 11810 | `3bf29b64f78c198c41bbfd3d1db2dee7fdb0fef2e84db127621a4d496afa79b9` |
| test_current_installation_cli.cjs | 4440 | `37a8a04c7d85606736473b6fd4624dee5f3b8a1a97d9e528da7a886503d56201` |
| test_main_new_point_ui_binding.cjs | 17413 | `a87044277c2d33d56c56cb86932f6bd7a21bd37ab32b30e99ea67bffb7e9ef8f` |
| test_automatic_main_chain_audit.py | 12246 | `7d448664813378a920aa656b64eda6dd4b4e8f06e4826c088a9436c929e0024f` |

父后续必须在实际新completed acceptance及明确v4 selector产出后运行正式只读loader/CLI，才可生成当前UI gate或派实际审计。本机合同通过没有替代该尚未完成的现场材料。
