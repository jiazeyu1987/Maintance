# MAIN UI 显式历史源码 custody CLI 接线

## 目标 / 当前状态

原 Python preflight r3 已实际 PASS；真实 UI CJS 仍仅传 selection/public-summary，遗漏已明确的补充 custody。仅修改 automatic_incremental_ui_acceptance.cjs 和新测试、本日志，保持旧调用、原生限额、既有receipt/gate不变。不启动Playwright/HTTP/SSH/Docker，不提交。状态：BDD / RED待执行。

## 经验门禁

- Trigger：已成功独立preflight后，真实UI重复正式本地读取遗漏显式证据。
- Preflight check：核实际runMainInstallationCli调用/argv，精确MAIN r7 selector与当前cycle；custody必须真实绝对PRIVATE文件、单链接、无路径别名，完整字节SHA及前后identity保持。
- Blocker：未显式输入、wrong scope、路径越界/别名/硬链、内容或identity变化、Python摘要未包含完全同一pin均阻断。
- Verification：真实临时文件/硬链/读取间篡改的有限Node协议测试，原生调用argv和原limits全核；旧Node回归。
- Forbidden action：不使用env或默认路径fallback，不改旧回执或fresh gate，不伪造Python历史完成，不以本机协议测试代替UI。
- Evidence：父已审Python source-role合同及实际r3；新测试原TAP/native/hash记录。经验索引命中运行资源依赖闭包和原始输入保护，沿既有正式checklist。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；无参数argv保持原样，有参数失败显式报错。
- 是否从根因和长期维护角度解决：是；跨语言参数合同与物理证据闭包同时绑定。
- 是否存在临时补丁或绕过：否；限定已批准r7/cycle，不能扩为任意历史映射。

## BDD

1. Given显式r7 selection/main-r7-20261110 cycle和真实private custody，When执行本地Python CLI协议，Then仅追加两个argv元素，600000ms/16MiB/no-shell原限额保持，记录原始输出后核summary.inputPins同pin及文件前后identity。
2. Given无参数，Then既有argv/native/limits逐值保持。
3. Given错误cycle/selection、相对或PRIVATE外路径、..、软硬链接/别名、缺失/过大文件，Then在spawn前拒绝。
4. GivenPython成功返回但缺失/错误custody pin或运行间实际文件变化，Then保留原native stdout/exit并拒绝。
5. Given缓存summary再入门禁，Then仍核同一原custody pin/identity，不能用修改后的新文件替代。

里程碑：精准RED→最小GREEN→受影响Node回归→冻结交父。只边界spawn协议可由测试明确提供；文件/identity/SHA均真实，不能称完成历史部署。

## RED

`node --test main_ui_source_custody.test.cjs` 实际17 FAIL / 0 PASS / 0 skipped，exit 1；CLI未识别参数，缺少显式scope、物理文件和摘要绑定，后续缓存复核函数不存在。输入SHA前后保持。原始stdout/stderr及命令、退出码记录在PRIVATE/main-ui-source-custody-red-r1.{json,stdout.log,stderr.log}。允许进入最小实现；未调用Python历史读取、页面或服务器。

首次最小实现后17项全部PASS。另补已要求的alias范围和重复门禁四个有限真实边界：Windows真实junction被拒、slash规范表示同物理pin被接受、删除缓存参数被拒；真实NTFS alternate data stream实际进入spawn，因此alias-red-r2记录4项中1 FAIL/3 PASS/0 skipped，exit1。随后对PRIVATE相对成员明确拒绝冒号，保持原文件/完整SHA校验；不改变其它路径/历史reader。

## GREEN / REGRESSION / 冻结

`node --test --test-reporter=tap --test-concurrency=1` 执行本任务目录内下列8文件，实际116 PASS / 0 FAIL / 0 cancelled / 0 skipped / 0 todo，native exit0，64.544秒；所有9个输入文件（driver+tests）完整bytes/SHA前后保持。

- main_ui_source_custody.test.cjs：新21场景。
- main_ui_local_verification_transport.test.cjs：原native失败/输出/限额和无参数argv。
- main_ui_deployment_root.test.cjs：原build/root/缓存闭包。
- automatic_main_cycle_ui_contract.test.cjs。
- automatic_stage_ui_contract.test.cjs。
- automatic_ui_browser_mode.test.cjs。
- test_main_new_point_ui_binding.cjs。
- automatic_ui_login_wait.test.cjs。

原命令、输入pins、退出码和完整TAP/stderr存PRIVATE/main-ui-source-custody-regression-r1.{json,stdout.log,stderr.log}。`git diff --check`本owned driver通过。本阶段仅边界协议测试，真实文件/硬链/junction/ADS/篡改均由操作系统执行；没有运行Python历史完整读取、Playwright或任何网络服务。

实现冻结：CLI可选参数仅允许main-r7-20261110及原b5/r7/v4 selector；严格PRIVATE文件原件在spawn前/后、缓存使用及最终closure处复核，Python摘要必须含同一物理pin，原native保留该pin。无参数原argv/native结构/timeout/maxBuffer/shell保持。旧回执、selector、fresh r3 preflight与Python reader均未修改。状态：本机实现与必要验证完成，等待父审/独立运行和提交；不宣称真实UI已通过。
