# 控制暂存与激活共享只读门禁

## Current Status

ready_for_closeout。独立只读模块与必要验证已完成并冻结，待父代理审查/提交及 stager、observer 正式集成。属于已批准的控制代次升级重构；父代理按 Subagent-Driven Development 分派。本阶段仅新增 `main_program_control_runtime.py`、`test_main_program_control_runtime.py` 和本专属记录，未修改 activation、stager 或其他 owner 文件；未访问服务器、构建、提交或生成实际部署证明。

## 目标、里程碑、预期验证

将 activation 既有进程、unit、worker、业务容器、挂载、历史回执和完整包门禁提取为正式 `RuntimeGates`，供 stager 在同一物理锁内完成 before → 独占暂存 → 实际候选构造门禁 → preserve。共享模块没有 systemctl 变更、回执轮转或业务命令；原 `CANDIDATE_GATE` 由 stager 原样复用。

1. 固定显式 spec/run/pin/read/proc/lock 边界与 BDD，先运行新测试 RED。
2. 最小提取实现，真实本机文件和子进程协议验证；Linux 锁场景由父统一执行。
3. GREEN 与受影响原门禁回归，记录 SHA 并冻结；接线交父协调，不能永久保留远程 disabled。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。进程消失仅允许处理遍历 `/proc` 时既有 FileNotFound/ProcessLookup；其它异常透传；门禁失败阻断下一次暂存。
- 是否从根因和长期维护角度解决：是。将共享行为置于单一新模块，stager 正式调用，后续 activation 接线使用同 API，禁止复制完整远程脚本。
- 是否存在临时补丁或绕过：否。当前 activation 暂不接线是父要求的冻结边界，不作为长期双实现。

## 经验门禁

- Trigger：控制代次暂存/激活共用现场只读准入和历史保全。
- Preflight check：显式绑定原控制器、进程 argv/环境/limits、unit/dropin、完整包、原业务快照、mountinfo/fstab、原历史和共享分层 custody；同一已持物理锁在阶段首尾核验。
- Blocker：缺原件、PID/argv/环境/文件/挂载漂移、活动 worker/resource、旧包成员变更、新路径已存在、锁失效或不合法 source/target 绑定。
- Verification：真实临时原件、实际本机命令子进程/显式 systemd/docker 协议边界；前后篡改拒绝；原门禁受影响回归，零 skip 才能记最终 GREEN。
- Forbidden action：假称本机协议 fixture 为远端成功、跳过包内容/旧历史、重启业务/Docker、轮转 receipt、改公司 NAS、改变 activation 原失败续办。
- Evidence：上位 `control-generation-upgrade-refactor-design.md`、`control-generation-activation-v4-tdd-log.md`；`docs/experience-index.md` 的包清单身份、自动增量与恢复周期、多机器接管门禁。

## API 与责任边界

`RuntimeGates(spec, *, verify_environment, verify_custody, lock_guard, run=None, pin=None, read=None, paths=None)`：显式外部边界；默认真实 stdlib `run_command` / `pin_file` / `read_pinned` / `RuntimePaths`。生产 paths 读取固定 `/proc`、`/etc/fstab`、resource reservation 和登记文件，测试可映射到真实临时目录；不得替换验证结果为成功。

方法：`verify_process(row)`、`verify_package(row)`、`original_units()`、`no_workers(rows)`、`snapshot()`、`guard()`、`retained_custody()`、`original_inventory(custody_observation)`、`before()`、`preserve(before, documents_created=...)`。验证器依赖为既有 environment 与唯一 custody owner 正式函数；导入模块无 I/O。`before` 拒任何新文档路径已存在并核九个保留文档，`preserve` 仅在明确已完成暂存时读取新文档，且旧环境与业务必须保持。

物理锁由 stager owner 按原 source/target 登记持有，本模块在每阶段首尾调用显式 lock_guard；实际 source epoch/来源计划和 `CANDIDATE_GATE` 仍必须由同一持锁编排完成，不由历史 metadata 代替。返回只读观察事实，不签发 staged/activated 成功。

## BDD

- Given 同一旧控制器和真实 proc/unit/config/package 文件，When 验证进程，Then 精确 PID、argv、环境、可执行文件和 65536 limits 全部吻合；任一漂移拒绝。
- Given 已持同一物理锁和无 worker/resource，When before，Then 核完整旧配置/包/回执/库存/业务/挂载、保留文档存在且新文档不存在，不执行写命令。
- Given before 与实际独占创建的新文档，When preserve，Then 全部旧事实保持且每个新 pin 吻合；新文件未产生、被篡改或任何旧状态变化拒绝。
- Given 旧包中非入口成员改变、历史 receipt/配置/原库存改变，When before/preserve，Then 不能仅凭 manifest 或 UI 状态放行。
- Given 已派发完 before 后锁失效，When 下一次 preserve，Then 失败发生于任意外部命令之前。
- Given 相同工作根下出现额外进程或 active reservation，When 准入，Then 拒绝；无关进程不作为本任务 worker。

## TDD

- RED：`python -B -X utf8 -m pytest <TASK>/test_main_program_control_runtime.py -q --tb=short` → 30 failed / 0 skipped / exit 1 / 4.01s；全部为新模块尚未存在，实际文件和子进程载体无 setup 错误。
- 第一候选：19 passed / 11 failed / exit 1 / 15.00s。定位两项 Windows 载体表达问题：真实 Python stdout 文本模式转 CRLF 与 POSIX systemd 原文不同；逻辑 Linux receipt 路径经 Windows Path 转反斜线。只修载体为原始 UTF-8 bytes 和显式 POSIX 逻辑路径映射，配置 PYTHONPATH 同值；正式环境/原件校验未降低。
- GREEN：同命令 → 30 passed / 0 skipped / exit 0 / 32.87s。

### 默认真实读边界补充 BDD

- Given 内存加载的新模块没有 activation import，When 未注入 run/pin/read/paths，Then 使用 stdlib 真实进程和固定宿主路径，不执行导入时 I/O；environment/custody/lock_guard 仍必须显式。
- Given 实际私有 JSON 原件与精确 pin，When 读取，Then 同次读取绑定 bytes/SHA/身份；内容漂移、硬链接、重复 JSON key 拒绝。
- Given 实际子进程退出非零并输出私密错误，When 默认 run 调用，Then 抛精确非零错误码且不把原始 stderr 写到公共错误。
- 新增 5 项，先运行 RED 后实现默认边界；物理 flock 由 stager 唯一拥有并实测，本模块仅消费显式 guard，不把 Windows 协议 guard 称为 Linux 锁证明。

- RED：5 failed / 30 deselected / 0 skipped / exit 1 / 0.54s，精确缺少 pin_file/run_command/default constructor。
- 第一候选：34 passed / 1 failed，真实 Windows fd 与路径的 ctime 时钟语义不同；独立临时文件诊断证实 lstat 为 creation time、fstat 为 change time。实现分别核同类 before/after 全身份，Windows 仅跨接口不比较 ctime，Linux 仍完整比较，不放宽同类时间或任何 inode/内容检查。
- GREEN：全部 35 passed / 0 skipped / exit 0 / 21.06s。
- REGRESSION：`test_main_program_control_environment.py test_installation_history_custody_layered.py` → 48 passed / 0 skipped / exit 0 / 4.47s。

### 完整 dropin 集合 BDD

Given 旧 unit/dropin pins 和 loaded DropInPaths 都未改变，但实际目录新增尚未加载的 `.conf`，When before 或 preserve，Then 必须与原激活同样拒绝，不能只核已加载文件。新增两个真实临时目录用例先 RED；原 fixture 增补真实目录和 existingNames 正式字段，不修改失败期望。

- RED：`... pytest <TASK>/test_main_program_control_runtime.py -q --tb=short -k unloaded_extra` → 2 failed / 35 deselected / 0 skipped / exit 1 / 2.60s；两处实际 `DID NOT RAISE`。
- 最小实现：`original_units` 同时核原 unit/dropin pins、实际目录身份、精确 `.conf` 名称集合；只接受显式 current 同 service 已登记 peer dropin，不能容许任意额外文件。
- 最终 GREEN + REGRESSION：`python -B -X utf8 -m pytest <TASK>/test_main_program_control_runtime.py <TASK>/test_main_program_control_environment.py <TASK>/test_installation_history_custody_layered.py -q --tb=short` → **85 passed / 0 skipped / exit 0 / 51.04s**。37 新场景与 48 既有环境/分层 custody 场景；所有源和测试在运行期间保持冻结。
- Python 固定 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，PYTHONPATH 为本任务现有 test-dependencies；无 Docker/SSH/业务动作。

## 冻结 API 与集成说明

- 独立观察方法不隐含 flock；observer 可做明确只读观测。只有 before/preserve 在阶段首尾执行调用方显式 lock_guard；stager 必须持真实同 PID 物理锁，锁实现及 Linux 实测归其 owner，不能用本机协议 guard 冒称实际 Linux 持锁。
- `before()` / `preserve(before, documents_created=True)` 返回 controllers、containers、fstabPin、mountinfoSha256、historyGuard、previousCustodyObservation、originalInventoryObservation、packagePins、documentsCreated。只返回原件观察，不签发部署成功。
- `sourceEvidencePins` 是调用方显式同主机范围：57 可核三份源证据，58/59 不读取57本地 registry。旧 activation 原来仅 source 角色读取三 pin；未来接线须保留原范围，不把含跨主机字段的旧 spec 无差别传入。
- `retained_custody` 调用唯一 owner 正式共享函数并逐成员核完整历史包；`original_inventory` 核原库存及 custody 全 verifiedPins。无 receipt 的57不制造 custody。
- 原 activation v1/v2/v3/v4、失败续办、receipt rotation、`CANDIDATE_GATE` 均未更改。父已明确本阶段不扩大 activation 修改；下一集成由各 owner 使用同一模块，不能复制完整远端脚本。

## 未完成的后续收尾边界

父任务已指出：历史 generation 读取旧 coverage 仍依赖临时 build worktree。准备与安装仍须严格核真实 HEAD/clean/全部源包字节；完成后读取历史需要独立持久证据合同，不能要求 worktree 永久存在。本阶段不改变该合同或删除 worktree，待真实控制升级及 Spug 验证后由父统一收口。
