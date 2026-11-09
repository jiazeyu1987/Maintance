# 完整资源观察生命周期 TDD

## Current Status

ready_for_closeout，本机实现与所需回归已通过并冻结，等待父独立复核及限定提交；尚未真实完整观察、安装、发布或完成上层任务。父已在 observation-plan/execution-log 批准 900 秒无完成工作期限、1800 秒绝对硬截止。两轮诊断未证实排序收益；本次不改变路径读取顺序、完整 SHA、原观察 v1、前后 equality 或安装/发布 reader。

## 目标、里程碑和预期验证

1. 先写真实子进程和真实磁盘文件的失败测试，保存 RED 原件。
2. 专属任务模块管理一个同容器独占观察、已完成工作进度及精确原 PID 查询；activation 仅接线，前后短命令共享同一硬截止。未知前次不可换 ID 绕过。
3. GREEN 后运行旧资源安装器、delta 和受影响 reader；旧测试仅调整 command(900) 的真实传输接缝，不删其它断言。
4. 冻结源码/测试/日志 pins 供父审。没有真实 Docker 观察、业务写入、安装、构建或提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。未知/停滞/硬截止/非进度 stderr/输出不完整均失败保留原件，不安装、不重派。
- 是否从根因和长期维护角度解决：是。完整工作量与固定总 900 秒冲突，以可验证完成工作续停滞期限且保留绝对上限。
- 是否存在临时补丁或绕过：否。原完整读和全部校验保持；不排除 observations、不改排序或缓存。

## 经验门禁

- Trigger：真实完整台账读取超时但原进程持续推进。
- Preflight check：父已批准文件范围/预算；旧未知进程已经精确终态，当前只本机测试；源码和旧测试字节已私密保全。
- Blocker：缺真实 RED、原未知 PID、试图重派/扩大预算、原文件/目录/完整 equality 守卫减少。
- Verification：真实本机子进程、真实临时文件、原回归、原始日志及精确 SHA；不把本机协议 fixture 当作容器或安装成功。
- Forbidden action：不调用服务器/Docker/浏览器、不改 publication/shared/B/C/产品、不重写旧失败原件。
- Evidence：spug-resource-ledger-observation-diagnosis.md、父 observation-plan、PRIVATE/ledger-lifecycle-baselines.private.json 以及本次测试原件。

## BDD（实现前）

- Given 单个真实进程按阶段和完整文件推进，When 超过初始停滞窗口但始终有已完成工作且小于硬截止，Then 返回原 JSON、唯一 dispatch、原件及实际退出码保留。
- Given 真实进程无进展、只发重复 heartbeat 或不断有效推进，When 达到对应停滞/硬截止，Then 失败并保留原身份、输出、原因；进度不允许无限延时。
- Given 同容器旧 operation 未知或原 PID 仍存在，When 换 ID 启动，Then 持久排他门禁拒绝；精确查询只能沿原 PID/startTicks/argv nonce，不派新观察。
- Given stderr 普通日志/畸形协议、非零退出、截断 JSON、身份变化，When 收口，Then 不将 stdout 当成功；原 stderr 仅私密保全，公共错误不泄露正文。
- Given 实际临时 JSON、空文件、硬链接/替换，When 执行原 file_pin 并启用进度，Then 完整内容与原结果保持，原 guards 仍拒绝异常；按路径输出不改。
- Given 前后实例读取耗时，When 执行观察，Then 这些短命令也消费首次开始的同一 1800 秒，不重新计时。

本机 Windows 进程测试使用实际 Python 子进程与系统进程身份；容器 argv/transport 边界明确注入，不宣称 Linux /proc 或实际 Docker 验收。

## 实际实现与审查结论

- 新 `main_program_spug_resource_observation.py` 只服务本任务完整观察。固定容器的持久 gate 与短时本地 mutex 约束同一 PRIVATE 下的观察，新的随机 operationId 无法越过未知前次；mutex 残留也明确阻塞，不自动删除或重试。操作 request/program/dispatch/stdout/stderr/worker/terminal 均只在 PRIVATE 排他写入。
- program 原件的只读句柄直接作为 Docker CLI stdin，stdout/stderr 是独占文件；宿主按 offset 消费 stderr，不使用 stdin.write/communicate 或通用异步队列。nonce 是实际 `python3 -B - <nonce>` 参数，Linux worker 从 `/proc/self/cmdline` 和 `/proc/self/stat` 读取实际身份；查询仍按同一容器、PID、startTicks 和 argv 比对。
- 只有完成既有检查阶段或完整 file_pin 后的进度可续 900 秒停滞期限；重复计数不续期。阶段、序号、文件数及字节数不能倒退，同文件数下字节数不能变化；DONE 只在 complete 阶段完成后接受，stdout 必须是完整 JSON。1800 秒硬截止不能续期，前后实例命令、原件准备和 exit 查询共享同一起点。
- 非进度 stderr、畸形/截断/超过 64KiB 协议行、失败退出、输出不完整、停滞、硬截止或身份变化一律失败；原始 stdout/stderr 保留在私密文件，公共异常只有稳定错误码。超时时仅结束本机 Docker CLI，不能据此断言容器 worker 已退出，也不自动向其发信号。
- 正常 CLI exit 0 和 DONE 仍不足以解除 gate；额外只读 `/proc` 查询确认原 PID 已不存在后才有 `remoteExitVerified=true`。随后原实例校验仍须通过。UNKNOWN 或原 PID 仍在时 gate 保留；查询原件身份未知、PID 复用或变更也不自动解锁。
- `prepare` 把新模块实际文件 pin 加入原 inputPins；原 `unchanged_inputs` 因而同时冻结真实传输依赖。AST 审查：旧安装器既有函数/类仅 `prepare`、`ActualTransport` 改变，没有删除定义。`HELPERS`、`file_pin`、所有验证/equality/dispatch/reload guards 保持；OBSERVE 的原任务、目录、历史、凭据、模块、实例检查全部保留，仅新增已完成进度及字节计数。仍按原 sorted path 完整读取所有 JSON。
- 原安装器测试只调整程序捕获及原 command(900) 接缝为专属 observation 传输；原成功输出、前后实例漂移、超时不重试、reload 的 240 秒及全部其它断言保留。其余旧测试未改。

## 实际 RED → GREEN → REGRESSION

统一命令环境：缓存 Python `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`；`-X utf8 -B`；`PYTHONDONTWRITEBYTECODE=1`；`PYTHONPATH=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies`。未安装依赖。测试最终不依赖 psutil；使用持有的真实 Popen 句柄、pid、args 和 poll 核验本机子进程。

1. RED：`-m pytest -q -p no:cacheprovider TASK/test_main_program_spug_resource_observation.py` → exit 1，22 errors / 2.36s，实际缺新模块。
2. 首实现 GREEN 尝试 r1 → exit 1，13 failed / 9 passed / 7.05s；暴露 Windows GetProcessTimes 参数类型遗漏，以及测试硬截止小于 idle 的无效配置。修正 ctypes 明确 HANDLE 参数及本机测试配置，未动正式预算。
3. r2 → exit 1，2 failed / 20 passed / 9.08s；真实本机 Python 启动/本地原件 fsync 超过短测试窗口，尚未收到 START。r3 → exit 1，1 failed / 21 passed / 11.02s，短命令测试的 0.15 秒已在 context 原件准备时耗尽，实际 command 未派发。测试改用 1 秒 idle，完成工作持续超过 1 秒，或真实 sleep 1.1 秒触发同一硬截止；保留原业务断言，不放宽正式 900/1800。
4. 协议追加 RED：`-k protocol_corruption` → exit 1，3 failed / 6 passed / 24 deselected / 5.20s；两项过早 DONE 和同文件计数下字节变化被真实子进程证实尚未拒绝。最小修正后，阶段回退、非法计数、截断/巨行仍拒绝。
5. GREEN r4：新33项 + 原安装器30项 → exit 0，63 passed / 70.11s，0 skipped。
6. 最终 REGRESSION：`-m pytest -q -p no:cacheprovider --tb=short TASK/test_main_program_spug_resource_observation.py TASK/test_main_program_spug_resource_activation.py TASK/test_main_program_spug_resource_deployment_delta.py TASK/test_main_program_spug_publication.py` → **exit 0，245 passed / 177.87s，0 skipped**。其中新36项，既有安装器/delta/publication 209项。新增实际文件替换、依赖 pin 漂移和前后实例共用硬截止测试均通过。

以上为本机合同。既有 fixture 在其临时目录创建独立 Git/执行微型真实 pytest 用以证明资源构建合同；不等于本工作区提交、正式构建或容器安装。所有运行源码/测试 raw bytes compile 通过，无 pyc。实际 Linux /proc 查询及固定容器完整观察仍待父后续真实运行；本机结果不能替代。

## 原件 pins（全部保留，无覆盖）

私密根固定为 `C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106`。

| 原件 | 字节 | SHA256 |
| --- | ---: | --- |
| ledger-lifecycle-red-r1.log | 28060 | fca60d92bffbc8af0ba6d042a4f59d07e40b8bd4a9052a78073c1cb1cb479bbd |
| ledger-lifecycle-green-r1.log | 43822 | a0bf97ce0fafd710b2a855c0da7296b6893c50c853f1c995c80cf1b347476650 |
| ledger-lifecycle-green-r2.log | 4499 | 35816af2080bfdacec0fde23520f6f6b227a996651f3c9869fff47438fd2c4cc |
| ledger-lifecycle-green-r3.log | 1569 | 06ab93ed65c266482051857221a07a3d81a2f4c4610d4b7d82df8a35debf0cf8 |
| ledger-lifecycle-protocol-red-r1.log | 9830 | 8a89d05d4c40b6bd6eafda4074f1071d70949fa370aa87da4599c1240295e326 |
| ledger-lifecycle-green-r4.log | 112 | 816c464019938d3af65d1aee631ea18cec39dc09664b5ce5a6a864326b2a33b0 |
| ledger-lifecycle-final-regression-r1.log | 357 | d369a49fe869a3716f7568afd55ed53f44f36d8764fcbaba82702dedcb6c131b |
| ledger-lifecycle-freeze-r1.private.json | 4170 | 25e7a66a047fde102b34747f8566cabd4491e2f3116372ca1d8a79d1a97f0e7a |
| ledger-lifecycle-review-r1.diff | 15507 | 261c148ebb8d2fab9d8005985879d1755194ef196670f4a319a5cdee395efe37 |

最终受测并冻结的四项文件如下；原始 Python 源和生成的完整 wrapper 均只 compile，不执行真实容器：

| TASK 文件 | 字节 | SHA256 |
| --- | ---: | --- |
| main_program_spug_resource_observation.py | 16511 | 1fa0b84025e236b5ab94f88f6eb0ecc5e73857dd24819a1be90f3e96bdb00a94 |
| main_program_spug_resource_activation.py | 36700 | df2157c40cd10a86219a183ac64cc5f7c7919646bec671c57e937c90ce6d93ee |
| test_main_program_spug_resource_observation.py | 14090 | 447e5dab1df7ffc805233b2e74045f118590a27378bdd0bfc54d85ee7c2c0734 |
| test_main_program_spug_resource_activation.py | 28690 | 10d8d841fa6a3367fb70ced69b0f764662e4033853f5b624446badeeecc4f911 |

受保护 `main_program_spug_publication.py` 仍为 82950B / SHA `ec4ca9f834332ef3b235c731f401b1c6435a49f08d2117be1acce1c35616aaae`。未改产品、共享 publication、B/C、旧失败原件、运行资源、构建或索引。

修改前私密副本 `ledger-lifecycle-baseline-main_program_spug_resource_activation.py.private` 35407B / SHA `979c3d6055b97e3552bce1cc5381f0f20a2bcd2cfedb027c4c634775b0672b20`；`ledger-lifecycle-baseline-test_main_program_spug_resource_activation.py.private` 27555B / SHA `4338df67a8021b0952408bd7772d4864490ef4fa369c2c0241c2792f2041a3c3`。父可直接 no-index 审阅，不能用 untracked 空 diff 当作未变。

## 父任务调用与失联处理

正式观察仍使用原命令入口，无需新 flag：`python -X utf8 -B TASK/main_program_spug_resource_activation.py --inputs main-program-spug-resource-observe-inputs-c7728ad-delta-r1.json --observe`。必须先完成父的实际经验门禁、输入 pins、旧 worker 终态和限定提交检查；本日志不是再次派发授权。

启动后可在 PRIVATE 精确读取 `resource-observation-<固定容器完整ID>.gate.private.json` 获得唯一 operationId，再读取 `resource-observation-<operationId>/` 的 request、dispatch、worker、stdout、stderr、terminal；不能扫描最新回执决定代次。stderr 的有效完成进度行前缀为 `SPUG_OBSERVATION_PROGRESS `，只含操作 nonce、进程身份、阶段和计数，没有台账路径/正文或凭据。

只读原进程查询：在本 TASK 加入 sys.path 后调用 `main_program_spug_resource_observation.query_observation(PRIVATE, operation_id)`。默认只写本地独占 query 回执，不解除 gate，不派发观察，也不发送信号。只有已明确允许本地解除前次观察门禁时，调用同函数 `release_exited=True`；它仅在本次实际只读查询确认原 PID 不存在、gate 仍指向该操作且未变时释放，并先保存 release 原件。得到的是 `EXITED_OUTCOME_UNAVAILABLE`，不能当作此前观察成功。

没有 worker 身份时返回 `UNKNOWN_PID` 并保留 gate；原 PID 活着、PID/argv/startTicks 不匹配或查询异常，也不放行。无法取得完整成功 stdout 时不补造结果、不从部分 ledger 续算；需要父先处理原执行终态，再决定是否启动另一独立完整观察。若本机在 gate/mutex 创建过程中中断，持久阻塞不会自行消失，须据原件明确处理；禁止直接删除未知 gate 或 mutex。
