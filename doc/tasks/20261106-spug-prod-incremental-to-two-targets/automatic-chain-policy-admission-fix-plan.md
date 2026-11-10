# 自动增量的链年龄与点数准入缺口

## Current Status

ready_for_closeout（本机准入修复子项）。BDD、三轮保留的 RED、新增54项及受影响137项回归已通过，父任务独立重跑共191项、零失败/错误/跳过，八个输入哈希保持不变；准备单独提交实现和证据。完整用户目标仍为 in_progress，本项未安装，后续交付与真实页面验证不得省略。

真实原操作376（65ed6552）已FAILED_RETAINED，Spug真实页面verify-r1也已显示FAILED，业务POST为0；不重试原编号、不覆盖失败材料。原采集SUCCEEDED且源程序已恢复，04:45 UTC独立五服务/语义健康PASS。没有发布新恢复点，没有执行本轮恢复。

## 已证实根因与目标

main-program-chain-age-failure-r6.json按当前请求owner、原根point/manifest pins核实：maxChainAgeSeconds=86400、maxChainPoints=16；根createdAt为2026-11-07T19:33:11.658174Z。归档元数据阶段2026-11-10T04:44:59Z根年龄205907秒（约57.2小时），原生REPOSITORY_NEW_FULL_REQUIRED正确拒绝。backend build_plan漏检这两项原owner策略，错误给READY父375，标准包在采集/上传后才检查当前年龄。

目标是将同一既有策略纳入产品计划及实际派发前门禁；到期/点数满时由正式BASELINE_REQUIRED状态和现有确认路径明确建立新FULL，不伪称增量、不放宽24小时策略、不重算旧清单。执行时再次核对策略，计划过期或并发状态变化应在停写/采集前拒绝。保留归档末端原有完整性和时限检查。

## 里程碑与验证

1. 只读核正式标准包与生产计划的合同及最小重构接缝；实际包来自冻结baseline加standard_fixes，不能只改lightweight源码。
2. 先BDD和RED：过期、恰好期限、未过期、点数满/将达上限、策略字段非法、未来时间、确认后过期；检查无法在错误READY下采集或停写。
3. 最小正式实现：计划按真实owner策略返回明确BASELINE_REQUIRED原因并绑定evidence；标准native在采集前再核准入。无新包格式/文件成员，不调整已知源/目标配置、不加静默改FULL。
4. GREEN/REGRESSION覆盖真实标准封包生成的入口、原计划和UI已有基线处理合同、lightweight边界。父任务独立验证后单独提交。
5. 后续才按正式干净发布worktree构建/验证并安装继任代次；既有用户安装授权持续有效，仍需新鲜门禁，不把本机测试当远端已修复。真实按钮应显示新FULL要求，按确认建立新链后再做增量。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；到期要求FULL是既有显式策略，必须在页面显示实际类型和原因；未知/非法策略保持BLOCKED。
- 是否从根因和长期维护角度解决：是；统一计划、锁内派发和原归档策略语义，避免操作结束才发现提交前已知的不合格基线。
- 是否存在临时补丁或绕过：否；不放大maxChainAgeSeconds，不捏造createdAt，不发布原失败半成品，不重派376。

## 经验门禁

- Trigger：自动选择全量/增量基线与真实标准包发布失败。
- Preflight check：先核实际installed package/manifest/owner/request合同；同时核maxChainAgeSeconds与maxChainPoints、源UUID/epoch、完整成功链与真实原时间；按冻结标准包构造器验证实际生成入口。
- Blocker：策略非法、源/epoch不符、时间不可解析或未来异常、不能在采集前阻止过期链、旧历史与失败被改写。
- Verification：真实RED/GREEN/REGRESSION、标准封包实际函数接线与拒绝顺序、原UIBASELINE_REQUIRED确认、父独立验证；安装/页面真实验证另留原件。
- Forbidden action：不调大策略绕过、不静默把失败改FULL、不改376结果/旧hash、不重发未知操作、不仅修改lightweight、不在主工作区构建/发布。
- Evidence：main-program-chain-age-failure-r6.json、automatic-main-20261110-r6-i1-verify-r1-result.json、请求owner原pin、45标准tgz common/repository_minimal.py第609行、backend recovery_control_incremental_plan.py。

## BDD

- Given 同源完整成功链与日志连续但根已达到最大年龄，When 用户预览增量，Then BASELINE_REQUIRED并显示到期原因，未派发业务。
- Given 链已有最大点数，When 预览增量，Then BASELINE_REQUIRED；允许新增后恰好达到最大点数。
- Given 字段无效或根时间在未来，When 计划，Then BLOCKED而非假称缺基线。
- Given READY后实际执行前已过期，When 标准native接收原增量请求，Then 采集/停写前失败，保留唯一原操作。
- Given 合法未过期链，When 选择增量，Then 保持原父点/根、UUID/epoch/连续性和完整读回合同。

按AGENTS Refactor Workflow使用现有子代理实施准入组织重构。父任务审最小文件范围与测试方案后才进入实现；子代理不访问远端/Docker/浏览器，不安装、不提交。
