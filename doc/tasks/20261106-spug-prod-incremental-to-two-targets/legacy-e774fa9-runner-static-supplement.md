# e774fa9 单点实验 runner 静态补充

## Current Status

completed（静态交付完成，实验未执行）。PRIVATE 单点实验 runner 已冻结供父静态审。此前计划/投影/44 点报告不变。本轮没有执行 runner（包括默认 prepare）、SQL、Docker、网络或产品测试，不登记旧点。实际执行仍待父审和排他窗口；父已核本机精确镜像尚未验证可用，不能用其他 tag 替代。

## 目标与验证

- 明确当前正式 helper 的 OS 需求；本机可用时不因原计划自加 Linux scratch hard quota 阻断。
- 默认 prepare 零 Docker；显式 execute 才可创建唯一实验容器，真实 importer/observer，无模拟成功。
- 仅给本次私有加载的 formal_sql_restore 模块注入 RecordingSubprocessFacade：真实 Popen，原 argv/stdin/stdout不变，仅把原 DEVNULL stderr 改成独占私密有界文件。
- 有界输入/输出、原生终态和精确 container ID 清理可审；只做 AST/字节等静态验证，不能把它称真实 RED/GREEN。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；任何原 pin/原生确认/归属异常显式失败，清理失败保留，禁止自动重试。
- 是否从根因和长期维护角度解决：是；单点实验仅复用正式 helper 并保全真实收据，不改产品，也不泛化成转换平台。
- 是否存在临时补丁或绕过：否；局部进程记录 facade 不替换全局 subprocess.Popen，不造 native 成功。

## 经验门禁

- Trigger：父认可单点实验方向后，需先审可执行 runner 与真实证据接缝。
- Preflight check：固定原 SQL/setting/version/material/工具 pins；确认 helper 实际 OS 条件和父资源排他；无本轮执行授权。
- Blocker：原件漂移、有限预算/进程终态或清理边界不可证；真实 Docker 阶段仍需父审核和排期。
- Verification：本轮仅 AST 编译静态检查/输入原 SHA 核验；实验和产品 RED 均未运行。
- Forbidden action：不 runner/SQL/Docker/网络，不改产品/旧证据，不设置假成功，不操作既有容器/卷/挂载。
- Evidence：原独立计划、当前 helper 源码、PRIVATE 新 runner及本补充。

## BDD（静态交付，真实行为待父审后验证）

- Given 未带 execute 参数，When runner 被调用，Then 只核本机 pin/配置并输出 PREPARED，不执行 Docker。
- Given 显式执行授权与精确输入，When formal stream_import 创建子进程，Then facade 调用真实 Popen、保留 argv/stdin/stdout/对象，并保全实际 stderr/退出及 helper 原 remote-ack/unknown。
- Given 超限、超时或身份漂移，When 实验失败，Then 保存原始失败，不重试，仅以精确自有容器 ID/标签清理，清理未知保留阻断。

## 正式 helper 的实际 OS 边界

原计划要求 Linux scratch 16 MiB 硬 quota 是本任务自加条件，本补充撤销这个执行前提，不改原计划的历史字节。`formal_sql_restore.main` 调用的 `require_native_runtime` 有 POSIX/CLOCK_BOOTTIME 门禁；本 runner 不调用该 main 或源捕获入口，仅调用已审直接 helper。`expand_checked` 的私密 mode 检查显式区分 `os.name`；`IsolatedTargetMySql` 执行的是 Linux 容器内命令；schema/data observer 的原生有界线程分支可从 Windows 宿主使用。这是源码接缝核对，不是 Windows 实际 import 或运行成功证据。

静态传递依赖清单保守覆盖 36 个 AST 声明的本地模块，包括函数内延迟 import；立即 import 的保守闭包为 9 个，未见模块级 fcntl/resource 等 POSIX 专用 import。部分延迟路径包含 fcntl，runner 不调用这些捕获/开放业务路径；实际 import 文件仍须逐 pin 相等，不允许以缺失依赖造成功。完整闭包在独立静态收据，未 import 产品模块。

`process_observer` 非 None 会进入 POSIX-only `drain_owned_process`，因此 Windows runner 明确使用正式 `process_observer=None` 分支。父已确认此边界可以用于本轮参考：完整 schema/data 仍走真实 `observe_data`，逐查询原始 native 收据不采集，结果固定 `perQueryRawProcessReceiptsCollected=false`；不把 helper 内部退出校验冒充已留存逐查询原件。导入器独立记录接缝如下。

## 单点 runner 固定行为

源文件为 `PRIVATE/legacy_e774fa9_reference_runner_20261111_r1.py`。默认只读固定的十份本机输入、11 个入口/解析器 pin、AST 本地依赖闭包及自身 pin，核 FULL 原 point/manifest/repositoryBinding、material 与原 SQL/setting/version 关系，输出 `PREPARED_LOCAL_INPUTS_ONLY` 和内容摘要；不创建实验目录、不 import 产品、不调用 Docker。原 backupId `smallapp-e774fa9f6f544aea8d3cbc9208d05938` 与 commonRecoveryPoint `sha256:47733f66685a7626a0e7f6260aca110d8e21e061a750af1b68e84ea5f35b8882` 分开绑定，原 FULL parent 数组必须为空。原版本文件在 material.versionPins，SQL/setting 在 payloadPins；不误要求 configuration 版本文件也是 payload 成员。

只有显式 `--execute`、唯一 `--operation legacy-e774fa9-<12位小写hex>`、`--docker-context` 和与默认 prepare 相同的 `--expected-input-sha256` 才进入执行路径。命令形状只是待审接口，本轮未调用。首先本地 context inspect 核精确名称及 npipe/unix endpoint，拒绝 tcp/ssh；随后只对预装精确 f5da image ID 做 inspect，核 linux/amd64，不 pull/load/tag 替代。容器与前代清单分开记录；创建与启动为两条真实 native 命令。所有容器资源/网络/tmpfs、原设置/空库/唯一 UUID、正式 guard、8.0.39 实测及 helper 限额仍保留。

局部 `RecordingSubprocessFacade` 仅替换本次私有加载的 SQL 模块的 subprocess 属性，finally 恢复；全局 subprocess.Popen 从未赋值。facade 核唯一真实 importer argv/PIPE 协议，真实 Popen 只将 DEVNULL stderr 换为 `xb`/0600 私密文件，返回原 Popen 对象。argv/stdin/stdout、原 helper 的 RECOVERY_SQL_EXIT 读取和 unknown 判断均不改。收据分别记录真实 PID/exit、helper 是否正常返回及原失败；成功依据是未修改 helper 正常返回且真实 exit=0，不伪造读到过的原始 stdout 字节。

stderr 文件每 50 ms 做软阈值监控，单 importer 阈值 256 KiB；容器数据 tmpfs 512 MiB、/tmp 32 MiB、1 CPU、2 GiB RAM/swap、pids128 保留。宿主 16 MiB、日志 2 MiB 是已知有界输入/独占输出加检查的软预算，明确不是 Windows 文件 quota。超限杀真实 client、保守提升 terminalUnknown、实验失败，原独占 stderr 原字节保留，绝不截断/覆盖/删除；可能瞬时越过阈值的边界不能改称硬限额。普通命令两管道分线程有界采集，任何截取原件都显式标 retained prefix/observed total/hash，超限不作成功。

原 gzip/展开 SQL 在导入 guard 前后独立核 pin，不能把 helper 目前未使用的 expected_digest/expected_sha 参数当成已完成内容核验。记录 facade 失败时保留原 importer 异常；只有真实 dispatch 后未确认的终态才保守提升 unknown，不能把前置 guard/intent 自行当真实 dispatch。完整观察只做一次，自比较结果另存并明确 `selfCompareOnly=true`，不能作第二次独立回放或备份时点证明。

finally 清理只核本次已保存的精确 container ID、image、精确 name/operation label，且禁止 ID 属于运行前清单；创建退出不明时只用本次精确唯一名称找候选，再核同一归属，禁止模式批删。只允许该 ID 的 `docker rm --force`，无 prune、卷删除、业务停服、Docker 重启、NAS 操作。真实本容器消失、运行前后 container ID 清单相等及本 runner 持有的真实 Popen 对象全部终止才可记清理 PASS；清单相等仅证明容器 ID 集合，不冒充业务运行态未变。原失败即便清理成功也保持。候选 reference 与最终 run-result 分开，cleanup BLOCKED 时最终始终 FAILED。

## 静态验证及冻结

本轮只用 Python `-X utf8 -` 读取源文件、`ast.parse`/`compile(AST, ..., 'exec')`（没有 exec 该 code object）、读取固定小元数据和校验 SHA。最终命令 exit 0 / 0.859 秒：runner 为 UTF-8 无 BOM、11 正式源 pin 相等、36 AST 声明模块可读、FULL 原件 ID/摘要/manifest/material 绑定相等、六份旧冻结交付 SHA 保持；断言没有给全局 subprocess 属性赋值，也没有调用 sql.main。实际没有 import formal 模块、执行 runner、pytest、Docker、SQL或网络。辅助读命令曾因 inline `\n` 构造出现 SyntaxError，改用 UTF-8 here-string 后继续；初稿元数据断言经真实字段静态核对修正，不将这些称产品 RED/GREEN。

- runner：40428 B，SHA256 `2cce41baaf6c94056eb7fbb1d6d4647aef0993aeed56aa65a595b78b35bdbd48`。
- 独立静态收据 `PRIVATE/legacy-e774fa9-runner-static-verification-20261111-r1.private.json`：16536 B，SHA256 `aec441e34af7b7bed5adfd533a11d6f9c3778239c9eb40c3f223a5eb30d86c89`。状态仅 `STATIC_CHECKS_COMPLETED_ONLY`，内含实际工具/依赖/原交付 pin，所有执行标志 false。
- 原执行计划保持 15376 B / SHA256 `6324bdd1bb4c111d138762a59e18d27bc8c11ab9880f9045b9528cd1785cca58`，其余五份原交付均按原 pin 核等。

父当前公开事实为 `legacy-e774fa9-exact-image-observation-20261110-r1.json` 的本机精确 image 未验证可用；随后远端只读 `legacy-e774fa9-remote-image-observation-20261110-r1.json` 证明原 ID 的 linux/amd64 与唯一 RepoDigest。依赖获取由父另记范围并决定，runner 不据该远端事实直接放行本机镜像，也未替换 image ID。本轮不进行产品 RED/旧点登记，真实参考实验及清理行为尚未验证。
