# 观察诊断警告通道 BDD / TDD

## Current Status

ready_for_closeout，本机实现与所需回归已通过并冻结，等待父独立验证及限定提交。父任务已保存实际 observation r2 因 CryptographyDeprecationWarning 失败原件，并负责唯一原 worker 的精确终态与 gate 处理。本阶段未操作容器、重派观察、安装或提交；不宣称上层任务已完成。

## 目标、里程碑和预期验证

1. 先用真实 Python 子进程 warnings.warn 复现当前把库 warning 当任意 stderr 的失败。
2. 只修改任务生命周期模块及其专属测试，新增明确 WARNING 事件、私密逐条诊断与终态汇总。activation/publication 冻结。
3. 测试正常 warning、warning 风暴、类别/身份/大小损坏、原生异常、非零退出及 warning-as-error；随后原 245 项加新增相关回归。
4. 保留所有失败原件、受测源码 SHA 及命令，冻结交父独立审查。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。warning 显式保存与报告，任意 stderr/异常/失败退出/损坏协议仍拒绝，不改变过滤配置。
- 是否从根因和长期维护角度解决：是。正式区分 Python warning 诊断与完成工作进度，不按库名或文本做例外。
- 是否存在临时补丁或绕过：否。无屏蔽、无依赖升级、无预算或完整校验放宽。

## 协议

WARNING 沿用 schemaVersion、operationNonce、sequence、identity，exact 新字段 warningCategory={module,name}、formattedWarning（warnings.formatwarning 原文）。单条原文 UTF-8 最多 8192 字节，类别 module/name 各最多 256 字符，仍受整行 64KiB 上限。WARNING 不带 phase/文件数/字节数、不续 last_work，也不改变最后进度。

本操作目录排他保存 warning-<sequence>.private.json；warning-diagnostics.private.json 汇总类别/数量和每条 pin。terminal 的 warningDiagnostics 仅包含 count、categories、diagnosticsPin，不直接放正文。原 stderr 原件仍完整保留；不改变实际 observation v1 返回。

## BDD（实现前）

- Given 真实 warnings.warn 和完整 JSON/complete/原 PID 退出，When 观察结束，Then 原结果不变，真实类别与格式化原文可从私密 pin 核对，终态明确 diagnostics 存在。
- Given 连续真实 warnings.warn 没有完成工作，When 到 idle，Then 仍 STALLED；warning 数量不提供进度或延长硬截止。
- Given warning 后任意原始 stderr/原生异常/非零退出/不完整 JSON，When 收口，Then 仍失败，warning 原件不丢失；warning-as-error 不被 showwarning 截获成成功。
- Given 伪造类别、身份、正文类型/超限、额外进度字段或巨行，When WARNING 到达，Then 真实失败，原 stderr 私密保存。

## 经验门禁

- Trigger：完整观察的库导入真实 Python warning 被原进度 stderr 判断拒绝。
- Preflight check：父先固定原 worker/nonce 终态与原件；当前范围仅本机两文件及本 TDD；先私密保全旧字节。
- Blocker：忽略 warning、按库文本豁免、warning 续期、扩大修改到 activation/publication 或实际容器。
- Verification：真实 warnings.warn 子进程与实际磁盘诊断原件、所有原回归、输入前后 SHA。
- Forbidden action：不改 warnings filters，不屏蔽 warnings，不调用 Docker/服务器，不追认原失败为成功。
- Evidence：父 warning-channel-plan、旧实际 operation、PRIVATE/observation-warning-baselines.private.json、下列 RED/GREEN 原件。

## 实际 TDD（持续补充）

统一缓存 Python `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 -B`，`PYTHONDONTWRITEBYTECODE=1`，`PYTHONPATH=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies`；无依赖安装，纯本机真实 Python 子进程与临时磁盘原件，未执行 Docker 或真实观察。

- RED：`-m pytest -q -p no:cacheprovider --tb=short TASK/test_main_program_spug_resource_observation.py -k warning` → 实际 exit 1，16 failed、36 deselected、22.15s。真实 warning 被原 stderr 守卫拒绝，终态未有 warningDiagnostics。原件 `PRIVATE/observation-warning-red-r1.log` 保留。
- 最小实现只增加 showwarning→WARNING、宿主 exact字段/类别/8KiB校验、逐 warning 私密排他文件、终态汇总。warning 风暴的每个协议行都检查原 deadline，避免单块缓冲区解析绕过停滞或硬截止；没有更新 last_work 或 lastProgress。
- GREEN：同命令 → 实际 exit 0，16 passed、36 deselected、9.85s。原件 `PRIVATE/observation-warning-green-r1.log`。身份损坏用例在生成事件前更改事件 identity，测试宿主真实身份拒绝，不用 producer 的重复参数 TypeError 代替。
- 父追加批准真实 `atexit` warning 场景：在 DONE 之后、实际进程退出之前仍可产生正常 warning。将等当前 261 项完整回归实际终态后再补 RED，只允许同一身份及严格递增序号的 WARNING；DONE 后 PROGRESS、第二 DONE 仍拒绝。此追加不改预算、完成状态或原 JSON。
- 第一轮完整回归：原245项 + 新16项，实际 **261 passed、0 skipped、exit 0、184.83s**；4项受测/保护输入 SHA 前后相同。原 session 46581 终态后才追加 atexit 用例和修改，未在该轮测试中改变输入。
- 追加 atexit RED：`-k atexit` → **1 failed / 2 passed / 52 deselected、exit 1、2.71s**。真实 atexit warning 被 `not self.done` 拒绝，完成后 PROGRESS 和第二 DONE 已按原合同拒绝。只移除 WARNING 分支的 `not self.done` 限制，保留身份、序号、类型和正文上限，其他分支原样。
- 全部生命周期 GREEN：不加 `-k` 运行同一专属测试文件 → **55 passed、0 skipped、exit 0、38.67s**。包含原36项、19项新 warning/atexit 场景。原245项加新增19项的最后完整回归在新独立日志执行，不覆盖第一轮。
- 最终 REGRESSION：`-m pytest -q -p no:cacheprovider --tb=short TASK/test_main_program_spug_resource_observation.py TASK/test_main_program_spug_resource_activation.py TASK/test_main_program_spug_resource_deployment_delta.py TASK/test_main_program_spug_publication.py` → **264 passed、0 skipped、exit 0、206.40s**。原245项加新增19项均通过，4项源码/测试/保护输入前后 SHA 相同。缓存 Python 原命令、实际退出、完整原始 stdout/stderr 及输入 pins 存在独立 r2 私密报告。

## 具体实现与审查边界

实现 diff 仅导入标准库 warnings、安装 showwarning 回调、精确 WARNING 解析/私密诊断及终态摘要，以及每条协议行的原预算检查。没有调用 warnings.filterwarnings/simplefilter/resetwarnings，没有 PYTHONWARNINGS=ignore，没有 cryptography/paramiko 文本判断。测试中的 simplefilter 只设置真实子进程的显式测试场景，并有独立用例验证正常运行的 filters 前后不变。

合法 WARNING 在 START 之后到原工作进程实际退出之间可记录，包括 DONE 后的 atexit 阶段；它始终不改变 phase/files/bytes/lastProgress/last_work/done。只有实际完整结果、exit 0、原 PID 退出证明、原实例/完整 v1 校验全部满足才成功。DONE 后 PROGRESS 或再次 DONE 仍失败；warning-as-error 仍是原生异常，不能转成 WARNING 放行。

每个有效 WARNING 原件保留格式化原文（含原路径/行信息），所以仅存本 operation 的 PRIVATE 目录。终态 warningDiagnostics 显式给出 count、按完整类别名统计的 categories 和 diagnosticsPin；其汇总原件再 pin 逐条 warning 原件。没有 warning 时三个字段为 0、{}、null。父报告可只摘取这个摘要及 pin，不输出 formattedWarning。

该修改没有触及 activation/publication、原完整读取/路径顺序/900与1800预算、gate/精确原进程查询/实例验证或公共 observation v1。实际 Linux/Spug 警告及整轮真实观察仍由父后续验证，本机子进程不能替代。

## 最终冻结与原件

本阶段只交付 TASK 下两项实现/测试和本 TDD 文档；以下是最终受测字节，raw source 与生成的完整观察程序均 compile 通过（未执行真实容器）：

| 文件 | 字节 | SHA256 |
| --- | ---: | --- |
| main_program_spug_resource_observation.py | 18567 | e88124854bb875c54d980e0e3861a8bae2b0483cbeafaef088f7e5fb4f4b1d34 |
| test_main_program_spug_resource_observation.py | 20392 | d00335ba6a0328fb9cee914f1e9de2693f040d5a513f2f10a2b911bb003a0c91 |
| main_program_spug_resource_activation.py（未改） | 36700 | df2157c40cd10a86219a183ac64cc5f7c7919646bec671c57e937c90ce6d93ee |
| main_program_spug_publication.py（未改） | 82950 | ec4ca9f834332ef3b235c731f401b1c6435a49f08d2117be1acce1c35616aaae |

原私密副本分别为 `observation-warning-baseline-main_program_spug_resource_observation.py.private`（16511B / SHA `1fa0b84025e236b5ab94f88f6eb0ecc5e73857dd24819a1be90f3e96bdb00a94`）和 `observation-warning-baseline-test_main_program_spug_resource_observation.py.private`（14090B / SHA `447e5dab1df7ffc805233b2e74045f118590a27378bdd0bfc54d85ee7c2c0734`）。没有覆盖前次失败或其 gate/worker 原件。

以下原件均在 `C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106`，排他保存，不作为真实安装或完整容器观察证据：

| 原件 | 字节 | SHA256 |
| --- | ---: | --- |
| observation-warning-red-r1.log | 14661 | 2d34975ae8bf748c8a08ff9ef8ce27e73c5a3b2d3cdaaaedfdde9a783f8f87a5 |
| observation-warning-green-r1.log | 116 | f565cb3325bf22c354f6893d5bf3ee1688861f873f58ab99a420b2df60eeb204 |
| observation-warning-final-regression-r1.log | 357 | d4dc971bd65996caf3bbaf4f4be9c1aa8608a4569df65addd07e92211eeb8c1f |
| observation-warning-final-regression-r1.private.json | 2439 | fbb7bba5c10018bcdb38bca8999f118bc105bde8564c7500ac2ba9da516f35c5 |
| observation-warning-atexit-red-r1.log | 1597 | b201d11254da0a0725ca46cdf1a77ac41f5fd2ed68057e43736721c0e4a528b5 |
| observation-warning-green-r2.log | 102 | 0c0f6e3196f292afac55c375a5b5bfb7148eb38e4c9fb3153c8d9ae6257a21bb |
| observation-warning-final-regression-r2.log | 357 | 4cf7a403f754537f00d3962b822f313ee73d065fbca882ceea523b82c24f1ea8 |
| observation-warning-final-regression-r2.private.json | 2438 | f9b6ef12c950948831e0617b94e3315bff82c31e7ae64addee500e31476f74b0 |
| observation-warning-freeze-r1.private.json | 3358 | a49dbe71ed0a8aa51242e4ee8af9b227c0c73ca3e69a1842d9b9b58ec7f24ec3 |
| observation-warning-review-r1.diff | 12676 | 89b16a97926dde20ff2d85640ffe46a50c1d99caa7db2f3ab397e809f9553ca5 |

父后续仍使用原 observe 入口和同容器 gate/原操作查询方式。成功或失败收口都可从该 operation 的 terminal.private.json 读取 warningDiagnostics；只有它给出的 diagnosticsPin 及逐条 records pins 能作为本轮诊断原件，不扫描最新文件代替精确 operation。正文保持私密。当前没有新的真实观察原件，本机 PASS 不能追认 r2 失败成功。
