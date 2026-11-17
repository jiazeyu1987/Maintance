# 增量备份耗时核查

最近一次已成功的增量`smallapp-bf67a867d3ec4e369ca31657c45e62c6`，从引擎开始前置分析/父链准入到最终SUCCEEDED，耗时**2小时3分40秒**。这是单次实测，不是每次固定时长或服务承诺。

| 阶段 | 原始阶段名 | 实测耗时（四舍五入） |
| --- | --- | ---: |
| 前置分析、父链准入校验 | archive-admission | 31分05秒 |
| 来源数据采集 | source-capture | 34分30秒 |
| 上传NAS | nas-upload | 3分44秒 |
| NAS回读 | nas-readback | 6分39秒 |
| 最终归档校验与链回读 | archive-final-verification + archive-chain-readback | 46分58秒 |
| 采集结果校验、清理、元数据及阶段间衔接 | 其余差额 | 约44秒 |
| 合计 | start.json至result.json成功终态 | **2小时3分40秒** |

原始起止：2026-11-16 17:10:28.341695 UTC至19:14:08.040260 UTC，即北京时间2026-11-17 01:10:28至03:14:08。精确差7419.698565秒。

Spug受理时间为2026-11-16 17:09:45.954198 UTC，受理到最终成功为7462.086062秒，即**2小时4分22秒**，包含约42秒派发等待。页面脚本observedAt早于受理，但包含登录和人工/页面确认过程，不将其当成精确分析阶段起点。

不能把采集子任务结束18:16:03、manifest生成18:19:56或归档中间完成18:50:37当作整个操作结束；最终repository owner的result.json明确SUCCEEDED、actualExitCode=0、finishedAt=19:14:08。

截至只读核查时间2026-11-17 06:45:11 UTC（北京时间14:45:11），当前新任务`smallapp-9d06cdef2d6d4a589db0506193629d5c`从06:23:12开始已运行约21分59秒，只有archive-admission-start，尚无阶段结束和result.json终态；结合目标线程原进程持续读取父链证据，仍处于前置父链校验。不能将这22分钟当作本次完成耗时，也不能据上一样本保证本轮在相同时间结束。

本轮此前失败任务4c3942的前置准入耗时24分52秒，之后来源容器身份不就绪而FAILED_RETAINED，不能混入成功样本或把失败用时当作正常完成用时。发布后来源登记已由所属线程更新，本审计未干预。

这些耗时对应现有主系统备份范围，不包含前序发现未纳入主链的发票助手、分贝通本地目录和OnlyOffice独立卷。本次未新增备份，也未改动活动worker或校验策略。

证据：source-timing.json保存固定白名单元数据的时间/状态字段；timing-summary.json为原时间戳和elapsedSeconds的汇总。Spug受理时间来自sixstep-20261116/spug/backup-INCREMENTAL-latest.private.json，仅提取时间和操作ID，秘密及浏览器登录态未复制。
