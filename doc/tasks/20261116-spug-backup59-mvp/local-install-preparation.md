# 本机 Spug 安装准备

目标：形成当前 18080 Spug 的精确可审查安装载体，不执行安装或重建。

里程碑：核 live 差异与任务；创建固定提交临时发布 worktree；生成仅本任务变化安装载体；交父任务审查。

经验门禁：已读 worktree-memory/restrictions/release-backup-restore；固定已提交5aeaaf1，构建输入只取本次新worktree；保留live无关修改与volume；不输出环境变量秘密，不改18081实例。

设计约束检查：fallback/吞异常否；长期维护是，正式配置变更与原入口重启；临时绕过否。

GREEN: experience-preflight -> PASS。只创建本任务本机发布worktree及准备载体，不执行运行安装。

状态：ready_for_parent_review；没有执行安装。

- 初始发布worktree：`C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-worktree`，提交5aeaaf1，未构建安装；发现live较本分支额外有正式修复，停止整文件覆盖方案。
- 只读证明其它开发分支38b43d3的entry/adapter/app.js/simple.js/nginx/index与live一致。simple.py仅live没有可选preservation字段支持，本次不更新它。
- 经父任务批准，以38b43d3创建integration-worktree并cherry-pick本任务92f2a96、3156318；两个冲突保留现有takeover与120秒预算，新prepare互斥/85秒预览并入。生成0bbf939、44cc4bb，不改int_main。
- 构建发布固定最终44cc4bb：新建`C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v2`，分支codex/spug-backup59-mvp-release-v2，clean。从该已提交worktree复制9个精确文件到私密payload；构建命令为Python按显式文件表复制并生成SHA计划。没有构建应用镜像。
- 验证命令：`python -X utf8 -m unittest test_prepare_target test_prepare_target_http test_prepare_target_native test_prepare_target_registration test_smallapp_cross_route test_smallapp_safety -q` -> 68/68 PASS；`node --test --test-reporter=dot ops/spug/smallapp-ui/prepare-target.test.cjs ops/spug/smallapp_ui_safety.test.cjs ops/spug/smallapp_restore_result.test.cjs` -> 90/90 PASS。
- 安装载体：私密local-install/apply_local.py（语法通过）；先比较现有精确文件和compose SHA，不匹配立即失败；备份旧文件，替换9文件，把原compose私密挂载改rw，然后原project仅recreate spug（no-deps/no-build/pull never），保留DB及named volumes。没有安装执行，不是PASS部署回执。
- supervisorctl只读检查显示没有控制section；运行entry PID3439，父为supervisor PID1。挂载由Docker定义，因此rw生效需要recreate；既有transfer-bootstrap调用smallapp_bootstrap恢复entry。父任务执行前需重新核当前活动任务及进程，不能仅历史记录证明空闲。
- 三个任务自有worktree均保留：首版发布、集成、最终发布；集成新提交尚未合回int_main，其他两个无新提交。发布完成后由父任务按实际归属验证并清理，不能提前删除集成提交。

## 安装后只读核验（2026-11-16）

- 父任务执行安装载体 exit 0，新 Spug 容器 `0c578f706938`；DB、18081 实例保持原容器。entry PID 9，未认证 prepare-target/config 返回 401，配置读取成功（目标 .59）。历史持久日志 BrokenPipe 不能作为新安装故障证据。
- 页面曾报 BRIDGE_NETWORK_UNREACHABLE。before-apply 与当前 compose 的 extra_hosts 均为 `host.docker.internal:host-gateway`，networks/network_mode 均未设置，未发现安装更改网络配置。
- 根桥配置的 18083 无监听，但实际 .57 safe 目录通过 selectionConnections 路由到 `intruoyi-program-selections-45dd7dc-r6.private.json` 的 32657；因此不能将 18083 无监听直接认定为实际页面故障，也不能启动旧桥掩盖问题。
- 实测新容器解析 host.docker.internal 到 192.168.65.254；该地址 32657、33659、18080 的 IPv4 TCP connect_ex 均返回 0。Windows SSH 分别在回环 32657/33659 监听。新容器未认证 GET 两个 selections 均返回 HTTP 404/TRANSPORT_AUTHENTICATION_REQUIRED，证明实际桥可达。
- 本阶段仅只读诊断，未修改 compose、桥配置或启动服务；继续定位实际页面所选 source/target 路由与认证目录结果。
- 使用新容器实际 live adapter 和现有私密凭据完成只读目录诊断：`HttpBridge(source_ref='intruoyi-57-safe-20261024-v1').selections()` 返回 1 个 application；同源增加 `target_ref='intruoyi-main-59-safe-restore-20261104-v1'` 同样返回 1 个 application。未输出凭据与目录详情。故目前不存在需要修复 compose 或恢复旧桥的证据，真实页面验收由父任务继续。

## source-only 静态补丁发布准备

- 父任务定位旧目标不可达会影响准备按钮目录，已另派实现 Agent 修正 app.js/prepare-target.js；本安装子任务只接收正式提交，创建本次 release-v3 固定输入并准备两个文件载体，不直接部署、不重启容器、不改 compose。
- 经验门禁：沿用本任务既有门禁，重新核 worktree/restrictions/release 文档；必须已提交输入、新建专用发布 worktree；应用前核对原安装九文件 SHA，拒绝覆盖并发改动；发布完成由父任务验证静态响应与真实页面。
- GREEN: experience-preflight -> PASS（仅本任务发布隔离与载体准备）。待实现提交后记录 release-v3 路径、目标提交、定向验证、是否产生新提交及最终清理。
- 私密脚本模板 `local-install/apply_static_v3.py` 仅允许两个 JS，默认只读 preflight，`--apply` 才备份并替换。尚无 v3 plan/payload，不能视为可部署。
- 更新：实现 Agent 已交付正式提交 `1bea1496770abf6813fab2afb8fe9dfd6bc38608`（实现 143f361、定向 JS 90/90 PASS）。执行 `git worktree add -b codex/spug-backup59-mvp-release-v3 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v3 1bea149`，新发布 worktree clean；没有产生新提交，没有自动合并 int_main。
- 构建命令为 Python 显式复制上述两个 JS，从 release-v3 已提交输入生成 `static-v3-payload/`、`static-v3-plan.json`。安装前九文件 SHA 再核通过。验证命令 `python -X utf8 local-install/apply_static_v3.py` -> preflight PASS；没有执行 --apply，没有重启或修改 compose。
- 交父任务审查后可执行 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/apply_static_v3.py --apply`。release-v3 当前保留、待父任务完成实际页面验证后删除并记录结果；本安装子任务状态 ready_for_parent_review。

## entry 单进程重载核验

- 只读确认容器 `0c578f706938` 的 entry PID 9、PPID 1；PID 1 是 `/usr/bin/python3 /usr/bin/supervisord -c /etc/supervisord.conf`。正式 program 为 `intruoyi-spug-backup-entry`，`command=python3 -B /opt/intruoyi-spug/smallapp_entry.py`、`autostart=true`、`autorestart=unexpected`、`startsecs=2`。没有 supervisorctl 或 HTTP 控制 section。
- 当前 entry 没有 SIGTERM handler。容器实际 `/usr/bin/python3` 所用 supervisor.process 源码确认：非预期退出进入 EXITED 后按 autorestart 配置 spawn。因此审核通过后可只对核实身份的 entry PID 发送 SIGTERM，让 supervisor 拉起新进程；不能发给 PID 1，不需要重建容器/DB。实际执行前应再次核对 PID 身份和父任务活动操作；本子任务没有发信号。
- 重载验证应记录旧/新 PID、PPID 1、原容器 ID 保持，以及未登录本地 entry GET `/prepare-target/config` 的 401；真实已登录操作由父任务继续验收。

## v4 未受理准备修复发布准备

- 父任务批准 entry 单进程重载方案；本子任务仍仅准备载体，等待父任务最终审查执行。实现 Agent 交付 f2cff77（实现 e322457，基线 1bea149），Python 31/31、JS 91/91 PASS，产品仅 prepare_target.py 与 prepare-target.js。
- GREEN: experience-preflight -> PASS。继续固定已提交输入、新建专用 release-v4；live 基线为 v3 两 JS + 44cc4bb 其余文件。默认只读核九文件 SHA、精确 entry PID/父进程及无本任务活跃 prepare 记录/entry 子进程；--apply 才备份、替换两文件，并在再次核身份后 SIGTERM 仅 entry，确认新 PID 与 401。
- 已执行 `git worktree add -b codex/spug-backup59-mvp-release-v4 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v4 f2cff77`，固定完整提交 `f2cff77bf13492de9ede64f60001a02e054190c2`；新 worktree clean，没有新提交、没有合回 int_main，待实际验证后由父任务清理。
- 构建以 Python 显式复制两文件到 entry-v4-payload，并生成 entry-v4-plan.json。验证命令 `python -X utf8 local-install/apply_entry_v4.py` -> preflight PASS；当前 entry PID 9、PPID 1、prepareRows=0、activePrepare=false、无 entry 子进程。原九文件符合 v3/44cc4bb 混合安装基线。
- 父审后准确执行命令：`C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/apply_entry_v4.py --apply`。目前没有执行安装、没有发信号；状态 ready_for_parent_review。

## v5 旧 bind 精确清理发布准备

- 父任务报告真实准备失败于三个旧本地 bind 导致 volume rm busy；实现 Agent 正式修 native，远端安装 Agent 准备精确配置及 native/config 载体。本子任务仅创建新 release-v5 固定正式提交供远端 Agent 使用，不执行卸载、清理或安装，不复制既有 Python/engine。
- GREEN: experience-preflight -> PASS。沿用已阅读 worktree/restrictions/release 门禁，只使用新提交的干净专用 worktree；保留 v1-v4 等待任务收口，不复用其发布环境。状态 waiting_for_implementation_commit。
- 父追加安全 failure detail 贯通：v5 将同时准备本机 prepare_target.py/prepare-target.js 精确载体与仅 entry 重载；远端 Agent 先交付 native/config 和 Spug 两 pin，本机载体后执行，两者均待父审。已复用 v4 方式准备 apply_entry_v5.py 模板；只读现态 entry PID 727、PPID 1、prepareRows=1、activePrepare=false、无 entry 子进程。尚无正式 v5 plan/payload，不执行安装。
- 实现正式版本 `8beac1a8529daf426bfbfa3663a7898a40eff091`（实现 f0b143a；Agent 回执 Python 37/37、JS 92/92 PASS）。执行 `git worktree add -b codex/spug-backup59-mvp-release-v5 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v5 8beac1a8529daf426bfbfa3663a7898a40eff091`；clean、无新提交、未合回 int_main、待父收口删除。
- 已交付远端安装 Agent 上述固定源码路径。Python 显式复制本机两个产品文件生成 entry-v5-payload/entry-v5-plan.json；`python -X utf8 local-install/apply_entry_v5.py` -> preflight PASS，PID 727/PPID 1、prepareRows 1、activePrepare false、九文件仍匹配 v4 已安装基线。
- 父审核并先执行远端 native/config 后，可执行本机命令：`C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/apply_entry_v5.py --apply`。本子任务尚未安装或发信号；状态 ready_for_parent_review。

## v6 控制桥明确客户端地址发布准备

- 父任务报告 v5 三阶段完成，但 publish 被旧 control 模板仅允许 127.0.0.1 阻止；实现 Agent 正式从 setting.allowedClientAddresses 覆盖新 control 配置，远端 Agent 已确认实际容器 TCP peer 为 192.168.109.82。本子任务仅等待正式提交后创建 release-v6，交远端 Agent 使用 native 源码，不更新本机 entry/JS 或重启。
- GREEN: experience-preflight -> PASS。固定已提交内容、新建专用干净发布 worktree、不复制旧 engine/Python、不执行安装；既有 v1-v5 保留待父任务收口。状态 waiting_for_implementation_commit。
- 已执行 `git worktree add -b codex/spug-backup59-mvp-release-v6 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v6 780a6ee2362aad254452c07197ee082a17ac2d2f`。固定 HEAD clean，未产生新提交、未合回 int_main；相对 v5 产品仅 prepare_target_native.py，其他为文档/测试。实现 Agent 报告定向 42/42 PASS；本子任务仅 `git status --porcelain`、`git diff --name-only 8beac1a HEAD -- ops/spug` 核发布输入，没有重复测试矩阵。
- 已把固定路径/提交交远端安装 Agent 运行载体 preflight；本子任务没有复制/部署文件，没有发信号或改配置。release-v6 保留，最终删除与父任务整体收口同步；状态 ready_for_parent_review。

## v7 控制进程环境发布准备

- 父任务报告 v6 客户端白名单通过，新 control 因 systemd 未传配置已有 PYTHONPATH 导致已存在的 jsonschema 无法 import；远端 Agent 已用正确路径验证 selections PASS。实现 Agent 修复 native 的 systemd 启动环境，本子任务等正式提交后创建专用 release-v7，仅固定 native 输入供远端安装载体使用，不安装组件、不更新本机 entry/JS、不部署。
- GREEN: experience-preflight -> PASS。沿用已读发布/worktree门禁，正式已提交内容、专用干净worktree、保留已有版本待整体收口；状态 waiting_for_implementation_commit。
- 已执行 `git worktree add -b codex/spug-backup59-mvp-release-v7 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v7 73dfd22ecac09f3ffda9da7070102fdf0676febd`。目标 HEAD 73dfd22 clean，未产生新提交、未合回 int_main；`git diff --name-only 780a6ee HEAD -- ops/spug` 确认唯一产品变更 prepare_target_native.py，另为文档/测试。实现 Agent 回执定向 43/43 PASS。
- 已通知远端安装 Agent 固定源码路径/提交进行载体 preflight。本子任务无构建镜像/安装组件、未复制部署产品文件、未重载 entry。release-v7 保留待父整体收口；状态 ready_for_parent_review。

## v8 systemd 219 环境文件路径发布准备

- 父任务报告 v7 新准备三个阶段成功，但实际 systemd 219 拒绝带引号 EnvironmentFile 路径，未载入既有 jsonschema 所需环境；实现 Agent 进行最小修复。本子任务等待正式提交创建干净专用 release-v8，交父与远端安装 Agent，不部署、不重启。
- GREEN: experience-preflight -> PASS。沿用已读发布/worktree门禁，输入必须为正式提交，保留旧发布工作区待整体收口；状态 waiting_for_implementation_commit。
- 已执行 `git worktree add -b codex/spug-backup59-mvp-release-v8 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v8 f3eb4b5271b56a4d119e22066070f7f5ca8d5cf5`。固定 HEAD clean，未产生新提交、未合回 int_main；`git diff --name-only 73dfd22 HEAD -- ops/spug` 确认唯一产品变更 prepare_target_native.py，另有对应测试。实现 Agent 回执 43/43 定向验证通过。
- 已把固定路径/提交交远端安装 Agent 运行 v8 载体 preflight；未部署、未重启、无本机 entry/JS 变更。release-v8 保留待父整体收口，状态 ready_for_parent_review。

## 真实附件页面验收脚本准备

- 父任务确认 v8 READY，正在恢复全量；本子任务只编写独立 verify_attachment_ui.cjs，父通知成功前不运行。复用 verify_business_ui.cjs 的真实登录和私密凭据路径，固定目标 http://127.0.0.1:18089，从 /infra/file/file 页面搜索本次私密基线的三个真实附件，通过页面打开/下载并核字节、SHA256、目标 origin。
- BDD: 附件真实恢复 -> Given 已完成全量恢复且登录身份有效，When 文件管理页面搜索并打开三个基线附件，Then 浏览器响应来自目标 origin，HTTP 成功、字节数和 SHA256 与本次基线相同，且业务写入数为零。
- 设计约束检查：fallback/吞异常否；长期维护是，测试脚本独立且只读；临时绕过否。不直接 fetch 代替点击、不修改业务数据/产品，凭据与附件详情不写公共日志。
- 经验门禁：已读 server-access/login-access，任务目标明确授权恢复目标只读验收；沿现有浏览器版本/执行路径。当前只准备脚本，真实 E2E 执行门禁与恢复成功通知由父任务掌握；状态 preparing_attachment_verification。
- 已准备 verify_attachment_ui.cjs：真实登录后从文件管理页面按完整路径搜索，核页面请求返回的真实记录 ID/configId 与同源 URL，再点击图片预览或 PDF 预览，捕获浏览器响应/下载的字节和 SHA256；拒绝业务写入与跨目标 API/附件请求，附件详情/截图/下载仅存私密目录，公共结果仅给计数和状态。
- DOM 依据：已核当前可读源码 `C:/Users/D01021/Documents/ChatGPT/IntRuoyi/IntRuoyiFronted/src/views/infra/file/index.vue` 的路径搜索、el-image、PDF 预览链接；旧 watch57-target-business.cjs/watch57-attachment-check.cjs 仅参考入口，未运行或复用其旧样本/目标。原 D:/ProjectPackage/AGENTS.md 本机不存在，浏览器包及 channel 沿本任务 verify_business_ui.cjs 已使用设置。
- 验证：`C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe --check doc/tasks/20261116-spug-backup59-mvp/verify_attachment_ui.cjs` -> PASS。尚未运行真实页面，不宣称附件验收成功。父通知全量恢复完成后可运行同 Node 路径加脚本与 `full` 参数；`incremental` 参数仍只验证这三个全量基线附件保留，不代替增量新增/修改/删除验收。

## I2 增量验收基线准备

- 父任务指定 I2 smallapp-e7b668792c8f4bce945a52f984d3c660，经 I1 20a1bb 到 FULL 3c2395，只读比对固定元数据，输出私密明细和脱敏计数；不读取载荷、不加载 298MB inputs、不执行恢复/服务器写入。优先复用 collect59 的既有 SSH 和新保留 Python。
- 预期验证：元数据原 pin 相符、链父子身份一致，提取各点表行数及附件新增/修改/删除；无变化须明确记录，基线不代表目标恢复成功。设计约束：无 fallback/吞异常，无产品变更，无临时绕过。状态 preparing_incremental_baseline。
- 已完成私密 `prepare_incremental_baseline.py` 只读采集：三个 point 原 pin、两个 capture 原 pin、三份引用清单和三份数据库摘要及两份增量范围元数据，共13份固定元数据；最终成功轮读取28,312,705字节，载荷读取0，服务器写入0，未加载298MB inputs。链父子关系、两增量binlog连续、受影响表摘要覆盖、无DDL均已核对。
- 初轮发现 objectReferences 不是唯一对象清单：8786引用行对应5001个唯一bucket/key，重复项内容完全相同。脚本修正为按内容一致性验证后去重，冲突仍失败；没有把重复引用误报为附件新增或删除。
- I1与I2的附件引用9074条、对象引用8786条（唯一对象5001）完全相同；每段及FULL→I2的对象内容和文件记录新增/修改/删除均为0。此链只能证明附件保留，不能证明非空附件增删改恢复行为。
- I2最终预期：erp_kingdee_sync_run=480（FULL476），infra_job_log=87458（FULL85151，I1 85859），dcc_registration_certificate_daily_run=72（FULL68）。qrtz_scheduler_state=1和qrtz_triggers=36行数不变但内容摘要变化。八个既有业务验收表行数保持full基线；全库计数不等同于租户过滤页面计数。
- 私密基线 `C:/Spug/runtime/private/spug-backup59-mvp-20261116/i2e7b668-acceptance-baseline.private.json` 保留885表最终预期及pin/变化详情；脱敏报告 `i2-acceptance-baseline-summary.json` 只含计数/表名/链标识。状态 baseline_ready，实际增量恢复未执行、目标未验证。

- 按父验收要求复用已保存13pin证据，两个private baseline.databaseTableCounts补三差异表，原8业务表保留共11表：FULL为erp_kingdee_sync_run476/infra_job_log85151/dcc_registration_certificate_daily_run68，I2为480/87458/72。differenceTableCountEvidence附三表内容摘要及原元数据pins；未重复远端读取。已交prepare_target_impl字段格式与来源。

## 运行引擎重复扫描只读审查

- 父任务发现本轮运行 selected_chain 仍对26GB归档做完整SHA，而本地正式源已移除。只读获取远端实际 minimal_plan/runtime 及加载路径，与已提交源比对，定位最小修复文件与依赖；禁止替换正在运行引擎、停止worker或扩成整引擎升级。安装时机限本轮终态后、下一次prepare前。状态 reviewing_live_engine_drift。
- 已保存实际两个引擎根的三文件源码及SHA：tools/common/minimal_plan为150行，runtime543行；与正式HEAD707d097对比plan59行、runtime458行。现有轻量selected_chain最初来自正式提交ba5fe2f，但当前runtime差625行且main preservation能力位不同，不能整文件覆盖。已交实现Agent实际旧源码，由其最小双文件修复。
- 确认旧check_pin(content=False)仍完整读取及SHA，False只表示不保留字节。旧selected_chain分别调用archived_tree、object_index_chain、physical_chain_inputs；旧runtime._initialize还汇集所有payload再hash，末尾archive-verification亦重复。因此仅改plan无法独立消除admission重复全量扫描。另一Agent元数据读量统计前三组约43.94GB，若第四组执行再26.09GB；本轮实际在ArchivePathGuard.capture句柄预算处失败，不能把预期70GB记为已实际读完。
- 真实control.programPins.recovery/repository仍指旧engine-main-program-2ac4b37，wrapper按__file__设置旧root/common且验证package.json每文件SHA；只更新tools目录不影响该执行入口。两root均为packageCommit6b39ef658008709b8b909dba4e16f890ad1d913c、包SHA70eebe93ea79e6681f70bc40c0a8bb7a3b3cb83f8c37830b309356c8c93980e3，两模块SHA完全相同。
- 必要正式安装：仅tools专属引擎两个模块及package.json两项files摘要/packageSha256，保留旧root。正式native生成新control时重pin recovery/repository到tools entry，PYTHONPATH前三个旧engine control/common/formal精确映射到tools同名目录；第四段现有site-packages保留。control.workingDirectory、control/owner.pythonPin、owner.formalModuleDirectory已正确，无需更改。模块不在prepared-inputs.manifest pins或当前control/owner的直接模块pins中，不需要伪改这些凭据/备份pin。
- 父确认本轮已自然FAILED_RETAINED、mutationDispatched=false、PROVEN_NO_MUTATION及共享锁释放，可在终态确认后准备/安装正式载体，再新prepare启动新control。验证要核下一轮实际program pin/cmdline及wrapper版本，不能仅看本机仓或tools文件。全程本子任务只读，无引擎替换/信号/服务器写入。

## v10 引擎与 native 精确安装准备

- 父要求准备正式载体，待实现提交后新release-v10，只tools引擎两文件/package及native与对应Spug pin；旧root不动，不apply。设计无fallback、保留已有MAIN能力，精确补安装漂移，无整引擎升级/新依赖。
- 只读核当前control service为active PID21493，tools/engine/control_entry.py；无active reservation、无recovery entry/minimal worker进程。apply需拿宿主锁后再核空闲，停止仅spug-prepare59-restore.service，替换后保持停止等待新prepare重建，保留原失败记录。
- native.dependencies没有package/两模块/旧engine目录项；retained manifest与owner/control模板无package.json pin引用，无两模块pin。故仅更新tools/package.json实际files SHA与packageSha256，nativeProgramPin经既有receipt/Spug链更新；nativeConfigurationPin不变，无目录pin需要伪造更新。证据v10-engine-dependency-pins.private.json、v10-engine-install-state.private.json。
- GREEN: experience-preflight -> PASS（仅载体准备）。状态 waiting_for_implementation_commit。
- 私密载体 update_engine_native_v10.py 已完成本机及嵌入远端 AST 语法检查；默认只读预检，正式源仅从 clean release HEAD 的 standard_sources()+safe_fixes() 生成两文件，package 保留其他条目及基线 commit，新增 installationPatch 记录实际修复提交，native 同一提交。apply 才拿宿主互斥锁、确认无活动恢复、停止唯一任务 control 服务、原子替换 tools 内四文件、验证实际 SHA/包装器 packageSha，并同步 receipt/Spug nativeProgramPin；不改原失败 target 或旧 root。
- 父要求等待后续 bind 合同修复，当前正式 e97c3881f30837f4798533f7cf71584a063a95a6 尚不固定 release-v10、不运行载体。实际只读核五容器 Mounts：mysql/minio/redis 为 RW bind，源精确位于 dataRoot/{mysql,minio,redis} 且列入 dataPaths，其余8个配置/私密 bind 为只读。旧 bound 的 WRITABLE_HOST_BIND_REJECTED 与 fresh_target 的 volume-only/volume inspect 两处必然拒绝合法新目标；证据 v10-target-mount-contract.private.json 已交父/实现Agent。无业务或服务变更。
- 已核 retained_dependencies：manifest 存在时检查保存 pins 后直接返回，不执行 copy_dependencies；实际 dependencies 没有 engine/package/两模块，下一次 prepare 不会从旧 root 覆盖 tools 引擎。状态 waiting_for_final_contract_fix。
- 父追加批准物理恢复路径重复读取一次收敛：最终载体增加已提交 recovery_data_files.py（verify_content=False 正式 API），如实现实际需要再含 recovery_data.py 单一 consistency 分支。私密载体现改为必须显式传 --module 指定最终3/4模块，只允许 plan/runtime/data_files/data 四者，拒绝缺少前三模块的中间版本；仍由新干净发布提交生成，基线 package SHA 固定，新增模块实际SHA须与该包声明一致。语法复核 PASS；等待实现最终文件集，未扫描载荷或安装。
- 最终正式提交 393be43f8e6c7ae5b7413b0fbe3754917110aae2（实现508f378，前轮实现0b1a037）。已执行 `git worktree add -b codex/spug-backup59-mvp-release-v10 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v10 393be43f8e6c7ae5b7413b0fbe3754917110aae2`；新worktree clean，未产生新提交、未合回int_main，保留待父整体收口删除。
- GREEN: `python -X utf8 update_engine_native_v10.py --checkout <上述release-v10> --commit 393be43f8e6c7ae5b7413b0fbe3754917110aae2 --container 0c578f706938 --module common/recovery_minimal_plan.py --module common/recovery_minimal_runtime.py --module common/recovery_data_files.py --module common/recovery_data.py` -> 只读preflight PASS。正式生成四模块/native编译通过；真实旧文件/包声明/receipt/Spug pin均匹配，无active/worker，control PID21493保留未停。未重复运行已由实现Agent完成的Linux11/native25/counts2测试。
- 预期新packageSha256=f2a40e9e9644ce3cc2d69099363c25bb4db5962660df53481fb06521d74ee38a；native SHA=c6fdd342202f3db76bf3a70bacb78d24bb610b3844100a8b8de256cb6cafff27。完整私密结果 engine-native-v10-preflight.private.json。已交父上述命令追加 --apply 的准确执行方式；本子任务未安装、未停服务。状态 ready_for_parent_review，安装后需新prepare生成 preparedEmptyTarget 与新执行pins。

## v11 已准备镜像合同精确修复安装准备

- 父确认 v10 已安装成功，新 full 准入耗时1.5秒，随后 target-checks 报 ARCHIVED_IMAGE_VERSIONS_INCOMPLETE，未写业务且锁释放。prepare 已加载/检查五镜像，但旧恢复仍要求空 imageBindings 映射。实现 Agent 正式修复 prepared 目标重复旧门禁；本子任务等待提交，新建 release-v11，仅替换真实差异 runtime（native 仅有差异时写），基线必须是 v10 实际安装包及文件摘要。
- 设计约束：无 fallback/吞异常，正式消除重复合同，无临时绕过；不重新扫描载荷、不扩大验证，停止服务/宿主互斥及旧root保护沿父已审 v10 方式。当前只准备默认只读 carrier，不 apply。GREEN: experience-preflight -> PASS。状态 waiting_for_v11_commit。
- 已核 integration HEAD=3dca5a9ced5ec26e1d973b84661a2c8d5d66d5d6（实现d804311）clean，执行 `git worktree add -b codex/spug-backup59-mvp-release-v11 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v11 3dca5a9ced5ec26e1d973b84661a2c8d5d66d5d6`，未产生新提交、未融合int_main、保留待父整体收口删除。
- GREEN: `python -X utf8 update_engine_native_v11.py --checkout <release-v11> --commit 3dca5a9ced5ec26e1d973b84661a2c8d5d66d5d6 --container 0c578f706938 --module common/recovery_minimal_runtime.py` -> 只读preflight PASS。live v10 runtime/package/两pin匹配，无active/worker，control PID29612未停。nativeChanged=false，因此apply也不写native或Spug pin。预期runtime SHA=f72733b86b4f005d82e129f692a2103e8d9873afb7f498f5ade7354cdf045c86；package SHA=48c48d3066e5af744ed40d15e5dee0e13dbb38117dca358020f5539d06c9ca4a。
- 以两个专用release的 standard_sources()+safe_fixes() 生成runtime对比，差异仅application_inputs六行：preparedEmptyTarget分支保留startOrder精确集合/长度，复用已做的实际镜像/挂载绑定后返回。私密 runtime-v11.diff 与 engine-native-v11-preflight.private.json 已交父；没有扩大复测或扫描载荷。准确apply命令为上述命令追加 --apply，父执行。本子任务状态 ready_for_parent_review，未远端写入。

## int_main 最终融合本地准备

- 父授权在真实恢复等待期从当前 int_main 25fe7edc47ee1cba9a4b85bcdc892d7819ea107e 创建本任务独立融合worktree，仅迁入 integration bcaf0e3f2efe48c455195307a94703ffedd1b813 相对已融合首版按钮0bbf939的最终任务增量。不部署、不改int_main工作文件、不清理任何worktree；实际完整/增量验收前不得合主线。
- 里程碑：新建融合工作区；一次迁入最终任务差异并解两已知冲突；最终结果运行必要定向集；交父review提交和差异。验收关注prepared空目标、按点恢复去重和Spug入口合同，避免逐历史版本重复测试。
- 经验门禁：已读worktree-memory/restrictions；仅操作本任务绝对路径，保留主线脏request-command-log和并发记录，禁止整branch merge/整文件覆盖引入其他线程尚未融合修复；无法分离语义冲突即报告父。设计约束：fallback/吞异常否；长期维护是；临时绕过否。当前状态 preparing_local_integration。
- GREEN: experience-preflight -> PASS。本地融合输入固定上述已提交版本，最终提交仅含本任务产物，验证通过前不删除工作区。

## v12 prepared SQL 最小读回安装与融合准备

- 父已审实现：仅生成common/recovery_data.py，prepared目标通过实际导入及SELECT1，不再全库逐行摘要/外排序；同操作同目标连续增量链消费保持。等待原integration正式提交后，迁入final-integration仅对应增量并受影响回归；另新建release-v12，基线v11实际安装package，仅data/package载体，native不变。
- 当前完整恢复仍运行；只读预检允许明确ACTIVE但不得停任务/安装。安装由父在终态后执行。不部署融合分支、不扩大测试或payload扫描。设计无fallback/伪造证明，未执行全库回读明确false/NOT_PERFORMED。GREEN: experience-preflight -> PASS（准备/只读预检）。
- 已执行新专用worktree：`git worktree add -b codex/spug-backup59-mvp-release-v12 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v12 31a670f883054a0cf09c4241a781327f117af46e`，clean、无新提交、未合主线、未删除。`update_engine_native_v12.py --checkout <release-v12> --commit 31a670f883054a0cf09c4241a781327f117af46e --container 0c578f706938 --module common/recovery_data.py`只读预检证实v11基线，ACTIVE=true、workerCount=0、control PID32674；没有apply或信号。预期data SHA a8b9c763dcca4e7c6b73bf2071f8a54242015c02836c95d7b05eec8ff00a30b1，package495d0f8de18f11d23df68180fbc5a6ff4f60075f329db6ebfa2a6a19055022b6，native不变。
- 父在上述预检后确认实际完整恢复已FAILED_RETAINED/ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED、mutation=true、active保留，要求暂停v12发布并等待健康检查修复；本载体未安装、不清active。final-integration已精确迁入bcaf0e3..31a670f三文件，受影响4测试PASS并另提交，未重复其他组。状态 waiting_for_health_contract_fix。

## v13 精确已终态预约下工具更新准备

- 父明确授权仅本任务bc9aafdc旧完整恢复的终态FAILED_RETAINED、child exit1且无worker，允许保持active原件的同时更新tools引擎/native；由随后新native按钮在锁内处理原预约。不得泛化为允许其他操作，不手工清预约、不绕过实际运行worker。
- 载体最小变更：固定完整operationId/target与原result/child证据，核终态及实际进程空闲；安装持共享lock后重复核同一证据、只停止本任务control，原active读前后字节保持。等待最终正式提交再新建release-v13，不提前发布、不apply。设计约束：无fallback/吞异常，正式工具更新和prepare重置职责分离，不改旧失败证据。GREEN: experience-preflight -> PASS（仅载体准备/只读核验）。
- 已固定新专用release-v13，分支codex/spug-backup59-mvp-release-v13，HEAD c4fa257d207c83c0179eaae83fa889b1861663b9，路径C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v13，clean、无新提交、未合回/未删除。命令git worktree add -b上述分支上述路径上述commit。
- GREEN: update_engine_native_v13.py --checkout上述路径 --commit c4fa257d207c83c0179eaae83fa889b1861663b9 --container 0c578f706938 --module common/recovery_data.py --module common/recovery_minimal_runtime.py ->只读preflight TERMINAL_RETAINED_ALLOWED，原四证据pins一致、bc9aafdc终态active、workerCount0、control32674未停。package SHA89ac1702b2bafd1a97ac12246d8fa28a82038764d069b1f9c0df9f8de73a3ff4，native SHA f758536b3933064ab198ef4b3dd3d23eba03ee155913f2764c0e6a4ade885b65。准确命令已交父，父添加--apply执行；本子任务未安装或清active。
- final-integration同步31a670f..c4fa257精确六文件增量无冲突，健康Linux5/5、native28/28均PASS；未重跑数据库或其他既有组。已提交该融合增量供父审，不部署融合分支、不合int_main、保留所有工作区。

## 真实全量验收 runner 修正

- 父确认真实FULL成功及11表匹配、登录成功；仅runner把route已abort的POST重复计成实际mutation，PDF内置viewer响应为合成HTML而非附件字节。授权修两个验收脚本，不改产品/服务/基线，不执行真实验收，由父运行。
- business与attachment区分blockedWriteAttempts与实际收到响应的非允许写请求，继续abort所有非允许写请求，不白名单workbench/context。附件采用任务私密目录独立临时浏览器profile，Default/Preferences配置plugins.always_open_pdf_externally=true，保留真实页面点击并核download保存字节/SHA/PDF魔数。仅node --check验证，不新增复杂测试。
