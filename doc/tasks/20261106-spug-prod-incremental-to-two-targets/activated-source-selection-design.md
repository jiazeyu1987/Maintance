# 来源独立升级的实际安装选择

## Continuation Gate

2026-11-11：继续本任务链，用户确认旧电脑 E 盘路径改为仓库相对路径；不新建任务、不重复 I1 或已通过的安装。接续当前来源组件 6968b58 的分角色安装识别和 I2 验收。

经验门禁：正式 v4 基线和原始回执保持不可变；新来源安装以逐步激活回执、实际包与配置校验值验明，纯证据识别不得冒充实时运行态验证。按 BDD / RED / GREEN 执行；真实 E2E 或服务器操作前须重新记录 experience-preflight PASS，授权范围沿用既有明确授权。

## Current Status

implementation_verified；实际完整load、Python80回归与5新context方法、Node48+23合同通过。原BOUND/v1继续禁止runtime准入。实际来源已6968b58、targets仍b5fa4c5，不能把旧单提交选择伪称当前安装，也不能把原I1提交回执重新签给新来源。真实当前准入、I2及三服恢复待验。

## 目标、里程碑和验证

1. 以原正式load_current_installation/v4结果为不可变基座；新增独立v2选择，显式引用该baseSelectionPin和顺序完整的实际来源activation证据，不改写基座。
2. 纯验证器验证每代真实完整回执的canonical远端receipt pin、previous/current controller连续、原build与实际双包差异、完整新engine/config/dropin创建pins、物理策略/epoch、仅来源重载与target/业务/挂载保持；回执不是实时观察，runtimeVerified始终false。
3. 实时准入分别使用source当前build/commit及各target原build/commit；Spug资源build保持其独立原提交。旧默认v4/BOUND消费者不变，旧提交回执只按其原选择读取。I2使用新的明确选择及新回执；不把所有roles伪称同一commit。
4. 原loader全部输入和overlay/每代proof/package/source code形成显式输入集合，消费后再逐SHA验证。实时服务器观察必须另核新PID/argv/配置/147成员及全部业务健康/容量/epoch/空闲；真实UI提交前再核，无未知结果重发。
5. 合同测试先RED，再GREEN/REGRESSION，使用已有真实捕获的base/proof/packages做纯解析验证；不伪造已通过服务器或业务恢复。新消费者实际预检、真实I2与其原生终态另验。
6. 页面验收显式增加source-activation选项及v3准入，仅该协议读取v2来源选择；既有v4/v1/v2默认行为保持。来源构建根使用6968b58，Spug根仍5651efc，原控制generation明确属于base，gate列明各角色build。新I2使用独立cycle，不重绑定原I1；所有原UI时限、实际点击、终态和输入SHA复核保持。

## BDD

- Given 原b5fa4c5基座和ddba4c6→019f462→6968b58三个真实来源激活；When解析v2；Then只替换57/source，三target和Spug完全保留，各role明确自身build；不声明实时runtime已验证。
- Given 缺代/乱序、previous controller或receipt不连续、原件SHA改变、未激活BOUND、额外角色/文件变化、捕获物理策略变更、配置/dropin/created pins缺项或原业务/target变化；When解析；Then拒绝，不改任何原件。
- Given原I1提交及旧v4基座；When解析新选择；Then二者原bytes不变，旧v1 BOUND仍不能进入runtime。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。旧协议继续按原语义；新协议必须明确选中且完整证明，不能从失败自动切换。
- 是否从根因和长期维护角度解决：是。安装身份按控制角色及显式激活链表达，不依赖单一全局commit冒充混合运行态。
- 是否存在临时补丁或绕过：否。不得跳过既有完整基座验证或伪造成功历史；实时准入独立。

## 经验门禁

Trigger：来源组件独立升级而target/Spug保持；Preflight check：正式base完整实读、全部真实激活链与新包、实时新进程另验；Blocker：缺代/漂移/角色错配/旧回执重绑定；Verification：真实原件正向及单点负向、旧协议回归、实际新来源UI准入；Forbidden action：重写旧选择或提交、BOUND当安装、把安装回执当健康证明、改NAS或业务数据；Evidence：unpolled-source-installation-finalized-r2.json、request-owner-source-installation-activate-r5/r6.json、request-owner-registration-post-ui-r3.json及PRIVATE实际full回执。
