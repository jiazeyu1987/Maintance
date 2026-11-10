# 真实 Linux 验证载体闭包修正

## Current Status

in_progress。载体修正及父独立107项回归已通过，等待同提交的实际Linux四组验证。e4e862b首次Linux source-policy54项成功，source-regression在收集期缺ops/spug/smallapp_adapter.py而exit2，未形成PASS证明。source-policy只在父进程使用records/planner；repository_minimal在包子进程运行，由source-regression及双实际包组分别证明。

## 目标与验证

BDD：Given 同提交完整必要源快照，When 收集六文件回归，Then 实际Spug adapter依赖存在；Given source-policy实际只加载records/planner，When 独立验收原件，Then 接受这两个精确模块并核每项原pin；source-regression和两实际包仍必须全3模块。未知或缺必需模块拒绝，任何已记录额外已知模块仍逐pin核验。

先新测试RED，再最小补正式REQUIRED_SOURCE_FILES中的真实adapter，按suite明确所需模块集合，不伪造import或删失败。原103合同回归及真实Linux四组需重新执行。最终source snapshot来自包含此修复的新提交，新专属worktree；旧e4原件保留，不能改完成命令/报告。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；按实际suite职责声明，完整3模块覆盖保持。
- 是否从根因和长期维护角度解决：是；显式运行依赖和真实执行模块绑定。
- 是否存在临时补丁或绕过：否；不人工import补数，不把collection error当业务RED。

## 经验门禁

- Trigger：真实隔离源测试无法收集或执行覆盖声明与真实调用不符。
- Preflight check：读原stdout/collection/events与源码imports，只补已证实必要闭包；隔离输入不变。
- Blocker：扩任意路径/任意模块、放宽fail/skip、原件漂移。
- Verification：新增正反例RED/GREEN、原合同、同提交实际四组完整0fail/error/skip。
- Forbidden action：不改原失败/实际loaded pins，不把模拟103项称交付验证。
- Evidence：chain-policy-actual-linux-e4e862b-20261110-r1.json、PRIVATE同目录原stdout/JUnit/events、后续新提交验证。

## 验证结果

RED：新增4项中2 FAIL / 2 PASS / 103 deselected；实际缺adapter与父模块集合声明不符均复现。最小修正后同4项PASS。父独立完整回归107 PASS / 0 failure/error/skip，159.88秒，输入前后全部pin保持；原始stdout/JUnit见chain-policy-parent-new-20261110-r2.json。尚未据此声明交付包验证完成。

## 实际variant职责修正

a4c279f真实Linux：source-policy54 PASS；source-regression123 PASS / 6 FAIL。六项均来自旧根目录身份测试：当前源码明确为LIGHTWEIGHT，root_identities为空且current仅检查deadline；STANDARD冻包的同类真实实现包含完整根目录身份核验。不能将该SAFE专属合同要求在LIGHT源码，亦不能删除这八项测试或放宽断言。

BDD：Given 原八项根目录身份测试，When 验证实际STANDARD包，Then 原文件完整执行并通过且实际repository_minimal来自该包；源码回归和LIGHT保持各自合同。正式suite_files按variant显式选择：source-regression保留另外五个文件，actual-package-policy的STANDARD包含原根目录测试，LIGHT不冒称拥有SAFE语义。所有输入仍来自同一提交，原a4失败保持；四组总原测试覆盖不减少。先路由RED，再最小接线、完整合同回归及新同提交真实四组验证。
