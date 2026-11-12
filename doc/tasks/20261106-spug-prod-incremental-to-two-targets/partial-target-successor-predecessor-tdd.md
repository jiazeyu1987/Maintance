# 部分目标升级承接的本机BDD/TDD记录

## Current Status

ready_for_closeout。实现与受影响验证完成并已通知父代理冻结；未提交、未访问服务器、不声明真实三服已完成安装。父负责正式partial全链一次加载、官方包实际差异核验与服务器/UI收口。

## 范围与设计约束

原57成功升级到0119156后，58/59仍b9。通过同一个完整per-host validator验证真实57回执，形成显式PARTIALLY_ACTIVATED前代；新的完整v3按host承接不同旧包及当前spec，全部实际ACTIVATE通过后才完整ACTIVATED。没有fallback、吞异常、临时绕过、伪造READY或合成另外两服PASS。产品源码和所有历史原件不在本次修改范围。

必要6个task源：`main_program_target_control_successor.py`、`main_program_current_installation.py`、`main_three_target_ui.cjs`、`main_program_target_control_activated.py`、`main_program_target_control_staging.py`、`main_program_target_control_runtime.py`。独立新测试为4个`test_main_program_target_control_partial_*.py`及`test_main_three_target_ui_partial.cjs`。

## BDD

- Given完整已验b9及真实57后继PASS原件，When partial load，Then只覆盖57当前身份，58/59、source/Spug/147history保持，partial明确installationVerified=false。
- Given缺host、非ACTIVATE、receipt/PID/candidate/native/API/peer漂移，When同一host verifier，Then拒绝；不得调整HOSTS或仅看顶层PASS。
- Given已批准8changed/12changed加唯一retry新增模块，When构造154后继，Thenreview逐件old/new SHA完全等于实际包差异；未知profile、缺/多/未变化成员、删除、错误count全部拒绝。
- Given新154包和旧153包，When同一stage/runtime合同，Then159独占写、170原pins保持，before旧153/after新154，147history及无worker/业务门禁保持。
- Given产品真实FAILED_RETAINED与未消费同source/point/target正式clearance，When v3 native/API判定，Then保留FAILED、只授权source可选、其它source精确拒绝；旧v1/v2不接受此分支。
- Given完整新v3和按host实际前代，When统一loader，Then三host完整验证后才ACTIVATED；partial无法进入UI，UI仍唯一I2→58并绑定旧两次失败op原件，旧op不得重用。

## RED → GREEN

所有报告在父任务私有目录`C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/`，未提交原始输出。

- RED `partial-target-predecessor-red-r1.xml`：13FAIL/1PASS，准确缺partial/v3入口；随后pure单host及真实本机文件加载GREEN `partial-target-predecessor-binding-r1.xml`：28PASS。
- RED `partial-package-red-r1.xml`：11FAIL，缺显式safe-tar count、row硬153及schema/count不匹配未拒；GREEN `partial-package-green-r1.xml`：11PASS。
- native首次`partial-native-red-r1.xml`为测试夹具缺baselineTargetPin的构造错误，明确不当业务RED；修正独立有限夹具后有效RED `partial-native-red-r2.xml`：1FAIL/16PASS，准确旧NATIVE拒显式FAILED分支。GREEN `partial-native-green-r2.xml`：17PASS。追加无retained context用例先RED，随后在最终回归18PASS。
- RED `partial-growth-red-r1.xml`：3FAIL/11PASS，真实safe tar仍默认153拒新154。GREEN `partial-growth-green-r1.xml`：14PASS。父追加必要program_native变更后先RED `partial-growth-native-red-r1.xml`首节点精确PROFILE_MEMBERS拒未审成员，再补源码固定8/12profile；完整候选/stage/runtime/真实本机文件v3链GREEN `partial-growth-green-r2.xml`：21PASS。
- Node新增v3首轮RED：1FAIL/7PASS，准确UNKNOWN_TARGET_SELECTION_SCHEMA；GREEN原UI+repeat+partial共73PASS，追加v3实际提交回执/旧op拒绝后最终74PASS。

## REGRESSION

固定Python：`C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`；`PYTHONPATH`仅加入父私有`pytest-runtime-8.3.5`，`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。

```text
python -X utf8 -m pytest scripts/tests/test_main_program_target_control_partial_predecessor.py scripts/tests/test_main_program_target_control_partial_package.py scripts/tests/test_main_program_target_control_partial_native.py scripts/tests/test_main_program_target_control_partial_growth.py scripts/tests/test_main_program_target_control_successor.py scripts/tests/test_main_program_target_control_successor_repeat.py scripts/tests/test_main_program_target_control_activated.py -q --tb=short --junitxml=<PRIVATE>/partial-target-final-regression-r1.xml
```

GREEN：336PASS，0failure、0error、0skip，128.06秒。含原v1/v2 successor/repeat/activated受影响全组；没有通过修改旧fixture/pin来获得通过。

```text
node --test --test-reporter=junit --test-reporter-destination=<PRIVATE>/partial-ui-final-r1.xml scripts/tests/test_main_three_target_ui_partial.cjs scripts/tests/test_main_three_target_ui_repeat.cjs scripts/tests/test_main_three_target_ui_contract.cjs
```

GREEN：74PASS、0skip，包含嵌入Python桥编译及原v1/v2入口/回执合同。`git diff --check`六源码PASS。

## 证据边界与交接

这些是有限单元/合同和真实本机临时文件tar/pin读回测试，不是E2E或服务器安装证明。历史source根在原测试夹具隔离，target完整包与后继文件均逐pin真实读回。没有启动浏览器、没有SSH/服务器写入、没有恢复或变更业务容器。

真实57 wrapper、父新partial原件与下一官方包最终diff/pins必须由父正式loader和原安装运行门禁验证；本机GREEN不能替代该步骤。partial完整祖先只加载一次，后继逐host复用同一已验base，不逐host重载47MB历史或以旧b9行假装57未升级。
