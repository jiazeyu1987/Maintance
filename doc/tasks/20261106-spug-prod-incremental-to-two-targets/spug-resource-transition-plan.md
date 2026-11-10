# Spug 已安装资源的正式版本转换

## Current Status

本轮历史读取接缝修复 ready_for_closeout：新增9项实际GREEN；联合106项原轮104 PASS/2旧载体FAIL，精确修正其历史scope后2项复跑PASS（92.50秒），全部零skip。父正式typed wrapper/v3实际完整prepare已exit0（14.281秒/1079pins），两11项投影、14资源、新entry152321和570秒预算一致。helper冻结32123B/b483f0db726992ee10764046d4a594418b77feb05c63fc96aaf9624a7a43dd11；B保持安装时b4619e。等待父独立验证/限定提交，整个业务目标仍在继续；没有重派安装、观察或业务写入。

## 显式历史 reader 托管与集合边界

父已批准 `resourceTransitionPin` 支持两个明确 schema：原 `MainProgramSpugResourceTransition/v1`，或 `MainProgramSpugResourceTransitionReaderCustody/v1`。后者精确字段为 schemaVersion、transitionCorePin、attemptPin、originalReaderPin、preservedReaderPin、currentReaderPin；只包直接原 Transition/v1，禁止递归 wrapper 或额外字段。原 helper path 必须是本模块唯一实际路径，原 pin 必须出现在对应实际 attempt；PRIVATE 内显式保全的原 raw 必须逐字节吻合，currentReaderPin 必须等于当前实际本模块。托管记录/core/attempt/原 pin/保全 pin/当前 reader pin 全部交叉绑定，进入新 B 的闭包。旧 direct core 在 reader 改变后明确拒绝，不能查找隐式 sidecar 或回退。

修复前保全安装时 29106B/dc3d9f01bc3e52204d6801683d3d05033c57afec7a3f89427091c8b0a7357a0b 原 raw。历史 preparation 使用局部 Records 从原 transition inputs 重建 B v1 权威集合；外层 v2/v3 输入和新 custody 仅进入新验收闭包，不改原 attempt 集合。候选 build 原有源码 custody 不扩权。原失败 v2 输入保持；父后续另建 verificationId v3 的原五字段输入，resourceTransitionPin 显式引用新 typed custody。此处不生成实际 v3、core 或安装证据。

BDD：Given 实际嵌套 B 入口及外层新输入，When 读取已完成安装，Then 原安装集合与原 attempt 严格全等，外层仅留新验收闭包。Given reader 已变更，When 直接旧 core 或错 core/attempt/原 pin/保全 raw/current pin/递归 wrapper，Then 明确拒绝。Given 正确显式 custody，When 新 B prepare，Then 完整原事件/命令/原件逐项核验且所有新旧绑定入闭包，原回执不改写。

设计约束检查：无 fallback/降级/吞异常；从独立 authority 集合与显式历史来源解决；无临时路径发现、改 pin 或空壳工作区绕过。经验门禁沿用本计划“Spug 运行资源依赖闭包”：旧成功写入只独立验收，原失败保留，所有原生命令与完整资源核验保持。

最新：转换实现已提交38c28df。实际只读观察75005 exit0、唯一安装49775 exit0/79.14秒，两个候选文件替换并读回成功，entry152321/startTicks121191318，完整14资源/七配置/155历史路由保持。原件及唯一gate保留。下一步为绑定真实转换核心的B v2六阶段只读验收；此处不等同完整目标完成。

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
