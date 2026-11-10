# Spug 已安装资源的正式版本转换

## Current Status

in_progress。必要实现验证通过：父原96项零skip通过；最后CRLF解析修复先精确RED、后2项GREEN并保留原失败；父最终正式reader已实际核565/r3完整161输入/14图/324pins，26.172秒PASS。新候选已在专属565提交checkout完成实际114 Python/92 UI；准备精确实现提交及正式只读观察。尚未安装或派发B现场验收；完整自动增量/三服恢复目标仍未完成。

## 目标、里程碑与预期验证

目标是安装 selection-read-budget-plan.md 的正式产品修复，并以实际新运行资源完成独立验收。七份配置、控制45/r6和原数据不重发。旧 c1/A 失败与成功原件保持。

1. 新增可复用的资源转换模块及测试，重用现有低层文件保全/替换、entry重载、完整运行守卫及原生命令记录；旧高层安装器不改。
2. 候选从新专属干净 checkout 的已提交内容产生，完整依赖图与候选清单逐项一致。新的 MainProgramSpugResourceBuild/v2 记录真实提交、checkout、文件和测试原件。
3. 差异必须精确等于前代完整文件集合到候选集合的全部非空变化，支持依赖集合内任意合法精确变化，不再硬编码本次两文件数量。当前依赖为14项；未知或未经审核的依赖增长明确拒绝。
4. 先保全全部变化文件，再逐项替换；每步核完整混合状态，最后只重载所属entry并核候选全集、配置、环境和历史。失败保留真实部分状态，不重试、不自动回滚。
5. B 增加显式 v2 输入 resourceTransitionPin，完整验证原 c1/A 与新转换后派生独立运行视图。两 guard 使用新14 pins/entry；Spug verify 的 spec.productPins 与 context.resource.files 同时由新转换证明更新；旧历史对象不修改。三服 HOST 验证及六阶段顺序不变。
6. 必要本机验证及父独立审阅通过后单独提交。实际构建/观察/安装/最终验收再记录前置门禁；真实页面与恢复另验，不以工具通过替代。

## 精确允许修改集合

- 新增 main_program_spug_resource_transition.py、专属测试与专属 TDD 日志。
- main_program_spug_publication_verify_only.py 仅增加显式 v2 输入/转换读取/运行视图派生；其专属测试新增该分支覆盖。
- v2 的 spug-verify 原正文顺序核9个来源/目标组合，每组共享50秒预算；外层原120秒不足。新分支按实际组合数乘正式50秒加120秒保全余量派生有限 native 截止，本次570秒；旧v1仍120秒，两guard原预算不变。测试必须证明预算包络和原正文/组合集合保持，不能等待实际超时后盲重派。
- 不修改旧 publication/v2/c1/activation/dependency、HOST/SPUG 正文、selection/collector 或产品配置。不得扩大历史源码 custody 绕过漂移。

## 复用及边界

使用 dependency.inspect_runtime_dependencies / validate_manifest_coverage、runtime_spec / RUNTIME_BODY、validate_reload_identity；activation.replace_archived / reload_program；continuation.ActualContinuationTransport；B 的已完成A/c1读取、schedule / execute_prepared。新模块提供 prepare_transition、observe_transition、execute_transition、load_completed_transition；默认纯 prepare，显式执行才写。不得复制旧高层发布逻辑或为当前问题重发成功配置。

输入引用冻结 B v1 inputs、完整候选 build、精确 delta、实际观察及唯一操作编号。真实未结束调用、同实例排他门禁、错误前态或缺原件均拒绝。安装前后均要求实际实例/完整文件、七配置、进程/环境、历史路由及保护对象一致，只有精确候选差异与所属entry身份允许转换。

## BDD / TDD

- Given 已证实前代与完整候选，When 精确非空差异安装，Then 先全部保全再替换，完整集合及实际新进程通过；空、遗漏、额外或伪不变项先拒绝。
- Given 配置、环境、文件或历史漂移，When prepare/实际步骤，Then 不越过该阶段，不修改原证明。
- Given 中途失败或未知，When 再调用，Then 原失败、部分状态与排他门禁保留，无自动重试或虚假成功。
- Given 转换原件完整，When 新 B 输入，Then 两个运行投影都绑定新资源，原输入分支行为保持；原件/回执篡改、仅更新PID或错误产品投影拒绝。

## 经验门禁

- Trigger：已安装依赖补齐后仍有真实产品缺陷，需要新资源版本。
- Preflight check：从实际已提交候选重建完整依赖，明确现网差异、全部原字节、唯一所属entry与配置/历史；核B旧输入只prepare而未派发。
- Blocker：旧helper源码pins漂移、旧失败重写、未知依赖、输入测试不足、未结束调用、配置或非所属对象变化。
- Verification：RED→GREEN→受影响回归、实际原生替换/失败合同、正式构建/完整观察/实际安装/六阶段验收、最终真实UI。
- Forbidden action：不直接改旧生成器，不重置旧hash，不重发七配置/三服控制，不重启容器或Docker，不改NAS/fstab，不宣称准备等于安装。
- Evidence：本计划、阶段B b85778f、阶段A e71d33ce 核心、实际r10中止及读取时序、新转换TDD和实际运行原件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；正式完整依赖和任意精确差异合同，避免每次硬编码当前文件数。
- 是否存在临时补丁或绕过：否。
