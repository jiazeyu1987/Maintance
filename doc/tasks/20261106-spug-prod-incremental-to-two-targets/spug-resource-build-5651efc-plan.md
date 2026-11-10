# 恢复目标读取修复的资源构建

## Current Status

in_progress；产品实现已提交5651efc5b9972b20bcacb50d0774e5862cbe8e6b。专属checkout已创建、同提交实际114 Python/92 UI零skip通过，161源码输入保持、完整14依赖及源码保全已产出build v2/r3，未安装。r1载体缺少未提交模板先失败、r2仅测试通过后的Node spec格式解析失败，原件均保留；r3使用同一真实原输出最终化，不将原外层exit1改成成功，不重复已通过测试。

## 目标与里程碑

- 为本次发布新建专属临时worktree：C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/release-spug-5651efc，固定上述提交；不得复用旧发布checkout或混入当前未提交的转换工具。
- 只消费该提交的Git已提交文件，核干净linked worktree、完整14依赖和所有测试输入；运行与该产品变更相同的114 Python及92 UI受影响回归。
- 产生正式build v2、测试原件和精确源码保全。新转换工具本身须另行通过本机验证并提交后，才用于正式观察与安装。
- 收尾记录是否产生新提交、是否需要合回int_main、最终删除结果；当前不删除仍需安装取文件的checkout。完整目标仍in_progress。

## 预期验证与命令

构建命令：git worktree add --detach <上述新路径> 5651efc5b9972b20bcacb50d0774e5862cbe8e6b。

验证命令：固定缓存Python -X utf8 -B -m pytest，沿selection-budget-parent-regression-r1.json的10模块；固定Node --test --test-timeout=15000沿同一记录的5个UI文件。运行目录必须是该新checkout，完整argv、退出、日志和前后pins独占保存；不使用开发目录文件补齐输入。

## 经验门禁

Trigger：产品修复提交后的正式资源发布；Preflight check：新专属路径不存在、目标提交已存在、原worktree/附件归属已核、Git checkout干净、全部输入来自已提交内容；Blocker：任一未跟踪或脏文件进入输入、回归失败、依赖遗漏或实际checkout不明；Verification：固定提交/全部源pins/实际测试/完整依赖图及后续独立安装验收；Forbidden action：不改Git换行配置、不用旧SHA冒充新文件、不操作业务或NAS/fstab、不清理其它任务；Evidence：本计划、5651efc提交和后续build/test/custody原件。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；完整依赖与已提交输入闭包，精确计算实际差异。
- 是否存在临时补丁或绕过：否。

## Worktree记录

目标提交如上。创建命令原session88162实际exit0；实际测试命令见spug-resource-5651efc-r3-execution.json，cwd均为本专属checkout，Python46.62秒114PASS、UI92PASS。构建载体原session45983外层exit1（仅Node输出解析），其两测试子进程均exit0；finalize-spug-resource-5651efc-r3.py实际exit0核原请求、输出、全部输入及干净Git后生成正式记录。新提交：未产生；合回int_main：不适用（本checkout未产生新提交）；最终删除：待发布不再需要后核对并执行，当前尚未删除。
