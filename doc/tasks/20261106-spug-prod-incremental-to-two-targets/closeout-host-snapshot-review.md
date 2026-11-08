# I2 后主机快照采集入口只读复核

## Current Status
ready_for_closeout — 已完成新增TASK只读采集器、57 closeout与最终verify_closeout精确I2绑定及13项本机测试。未执行服务器访问、浏览器或采集；58/59新安装PASS回执尚缺，现场执行继续由根任务在前置满足后负责。

## 目标与里程碑
- [x] 确认既有 observe_baseline.py <suffix> --phase closeout 能输出目标名称，但存在旧代次和控制API审计副作用，不可原样用于本次严格只读收尾。
- [x] 新增 observe_closeout_hosts.py，精确核安装PASS、实际service PID/argv/config pin和130文件SHA；敏感内容只存PRIVATE。
- [x] 已先向根任务报告缺口，再按明确授权最小改verify_host_preservation.py的57 closeout绑定；其它phase/旧367路径保持。

## BDD 与修复边界
- Given三服各自当前安装PASS且实际service argv/pin匹配，When I2后的严格只读采集，Then完整原始快照只存PRIVATE，公共输出仅摘要；不调用selections、Ledger或任何控制API。
- Given58/59缺当前PASS安装回执，When准备采集，Then本机失败，不连接服务器。
- GivenI2 submission/audit/terminal/source-restoration均指向同一成功操作，When57 phase=closeout保全，Then使用真实I2操作号和全部输入pins，after.observedAt晚于I2及来源恢复检查。
- Given任一证据缺失/失败/不匹配或已存在输出，When准备/保存，Then明确拒绝；原367及其他phase路径不变。
- RED/GREEN仅使用本机合同样例、真实临时文件和SCRIPT语法，不声称现场采集PASS。

## 既有入口的具体缺口
1. observe_baseline.py通过common.active_source_installation选择旧source-control-binlog-temp记录；57的旧target-installation.json在本次0d双根升级中按历史保全要求未轮换，因此会读旧owner/engine。
2. 该入口访问/selections?targetConfigRef=，可能经observe_main_target追加查询审计，不是无控制台账写入的快照。
3. 原verify_host_preservation.py给57 closeout填写旧new-incremental-point-verified.json（367）操作号，与最终I2不相符。

## 新入口与精确执行命令

只能在I2真实audit、UI terminal及source-restoration全部存在且PASS、58/59 automatic-target-installation-<suffix>.json各自PASS后执行。`--prepare-only`仅检查本机，不连接服务器。当前本机已核57双根实际PASS回执；58/59新PASS回执仍不存在，不能提前采集或伪造证明。

```powershell
$closeoutPython = 'C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$closeoutTask = 'doc/tasks/20261106-spug-prod-incremental-to-two-targets'
& $closeoutPython -B -X utf8 "$closeoutTask/observe_closeout_hosts.py" 57 --prepare-only
& $closeoutPython -B -X utf8 "$closeoutTask/observe_closeout_hosts.py" 58 --prepare-only
& $closeoutPython -B -X utf8 "$closeoutTask/observe_closeout_hosts.py" 59 --prepare-only
& $closeoutPython -B -X utf8 "$closeoutTask/observe_closeout_hosts.py" 57
& $closeoutPython -B -X utf8 "$closeoutTask/observe_closeout_hosts.py" 58
& $closeoutPython -B -X utf8 "$closeoutTask/observe_closeout_hosts.py" 59
& $closeoutPython -B -X utf8 "$closeoutTask/verify_host_preservation.py" 57 --phase closeout
& $closeoutPython -B -X utf8 "$closeoutTask/verify_host_preservation.py" 58 --phase closeout
& $closeoutPython -B -X utf8 "$closeoutTask/verify_host_preservation.py" 59 --phase closeout
```

各命令必须检查退出码，前一项失败不继续。collector同时拒绝已有PRIVATE快照或TASK公共摘要，使用独占创建，不能覆盖历史。保全verifier沿用原输出方式，运行前须确认各source/target-<suffix>-closeout-preservation.json尚不存在，不能用重复验证覆盖已有历史报告。

## 只读与敏感输出策略
- 远端仅systemctl show、Docker ps/inspect、读取固定配置/package/进程/mountinfo/fstab，以及MinIO/后端/前端HTTP健康GET。没有SQL、selections、Ledger、重载、停服、文件写入或数据恢复。健康入口使用新实际owner的frontendReadiness合同，适配58发布端口配置，不硬编码旧8081。
- 57依据automatic-control-installation-57的两个controller；58/59依据各自新PASS安装回执，校验currentReceiptPin，实际argv指向同一精确control pin/engine。全部为0d44578和相同130文件manifest。
- Docker完整Config.Env、配置文档、完整进程命令、挂载内容仅保存到C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/closeout-<suffix>.private.json，不输出到终端或提交。
- TASK/closeout-<suffix>.json及终端仅输出时间、主机、操作号、健康摘要、计数、配置代次与原件SHA、进程PID/命令SHA；标为OBSERVED，保全PASS由verify_host_preservation另行判定。
- 57 closeout报告核原I2所有证据pins、时间严格晚于I2独立源恢复、raw快照自身同操作/同pins/无控制API调用；旧367及其它phase保持原行为。

## 本机证据
- RED：新测试导入observe_closeout_hosts失败（模块尚未存在）。实现后6 PASS/1 FAIL是只读AST测试把字符串replace误判成文件写入；限定禁止os.replace后继续验证。
- GREEN：10项任务合同测试全部PASS（0.56秒、零skip），覆盖57真实双根回执、58/59缺/失败回执、错提交、I2缺证据、精确pins、快照时间及证据篡改拒绝。
- SCRIPT/全部改动Python语法、UTF-8、diff whitespace检查PASS。实际本机57 receipt选择PASS、2 controllers、remoteReadDispatched=false；58/59回执存在性均false。
- 根任务追加授权后，verify_closeout.py增加verify_automatic_source_preservation，只核最终来源保全的I2操作号和精确evidence pins。先新增3项定向测试RED（函数尚不存在），最小实现后13项完整任务回归PASS（0.34秒，零skip）；旧367及其它agent提交helper未修改。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。仅查明实际合同；缺口明确报告。
- 是否从根因和长期维护角度解决：是。复用既有快照协议和原保存基线，避免伪造或覆盖历史。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：I2完成后需要三服最终定义/其它业务运行态及NAS/fstab保全证据。
- Preflight check：核采集器当前安装选择、只读命令、输出字段与verify_host_preservation.py一致；原pre-install基线保留。
- Blocker：采集器硬编码旧代次或输出覆盖风险、验证器仍绑定旧操作号；先报告，不调用远端验证。
- Verification：本机源码/已有脱敏记录核查，精确命令和敏感输出策略交根任务。
- Forbidden action：不得运行采集、服务器命令、浏览器、改历史证据或擅改其他父任务脚本。
- Evidence：本复核说明及根任务消息。
