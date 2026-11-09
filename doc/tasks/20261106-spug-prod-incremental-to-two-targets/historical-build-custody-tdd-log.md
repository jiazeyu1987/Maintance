# 历史构建托管 A 阶段 TDD 记录

## Current Status

ready_for_closeout（仅 A 阶段，待父独立验证/限定提交）。本机实际 37 PASS、零 skip，生产/测试已冻结。父代理已审阅 dependency-assessment，仅授权独立 A 阶段：新 `historical_build_custody.py`、`test_historical_build_custody.py` 和本日志。B/C 现有 reader、coverage、安装、closeout 全部未改。本阶段未封存实际 461/154 输入，未操作实际 9 个工作区、服务器、构建或提交。

## 目标与里程碑

1. 固定精确 schema/API 和 BDD；用真实小型 Git/worktree、文件和 tar 得到 RED。
2. 最小实现独立标准库模块；GREEN 与自身负例回归；原 logical pin 不改。
3. 冻结三个限定文件，交父独立验证。不声称 B/C 接入或实际归档已完成。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。必须明确提供 custody pin；成员只由原报告派生，缺件即拒绝。
- 是否从根因和长期维护角度解决：是。封存/历史读取分离，原引用、raw bytes、Git blob 与物理归档同时核验。
- 是否存在临时补丁或绕过：否。无空壳 checkout，无重写旧 SHA，无环境缺失 skip。

## 经验门禁

- Trigger：历史读取仍依赖临时 worktree；A 阶段只实现正式托管原语。
- Preflight check：父计划/评估、experience-index、映射 powershell-memory、既有工作区归属和持久证据门禁；只改三个新增文件，UTF-8 无 BOM。
- Blocker：原报告集合不完整、commit/blob 不对应、raw 表示不支持、归档越界/漂移、测试环境不具备真实 Git。
- Verification：真实临时仓库提交、独立 worktree、实际文件/tar/删除后的读取；精确 exit/count/skip 记录。
- Forbidden action：不扫描 PRIVATE，不运行现场 Git status，不清理实际工作区，不访问服务器，不改其他 helper，不提交。
- Evidence：本文件、限定测试的实际输出；原阶段 assessment 仅是设计证据。

## 精确 A 阶段接口与 schema

API：`seal_build_custody(task, private, *, inputs, destination, repository) -> custody_pin`；`load_build_custody(task, private, custody_pin, *, repository) -> HistoricalBuildCustody`。对象提供 `read_original(reference, *, evidence_pin, purpose)`、`verify_original_inputs(references)`、`finish() -> verification_pins`。module 无导入 I/O，全部路径显式参数；不依赖 B/C 模块。

`HistoricalBuildCustodyInputs/v1` 精确字段：`schemaVersion, taskId, builds, sets`。

- builds 每项精确 `{id, kind, reportPin}`；kind 为 ENGINE_PACKAGE/SPUG_RESOURCE。原 build report 位于 task，必须 PASS；ENGINE 从原 `targetCommit/worktree` 取身份，RESOURCE 从 `sourceCommit/worktree` 取身份。id 唯一且不由短 commit 猜测。
- sets 每项精确 `{reportPin, field, bindings}`。field 只允许原报告的 `inputPins/sourcePins/files`；该原字段是非空完整映射，值只能是 SHA 字符串或 `{bytes,sha256}`。bindings 的 name 集合必须与原字段完全一致。
- binding 精确 `{name, purpose, buildId, originalPin}`。purpose 为 COMMITTED_SOURCE/REPOSITORY_SOURCE/TASK_ORIGINAL。COMMITTED_SOURCE 路径必须是该原 build 工作区下的 name，并在原 commit tree 中是 blob；REPOSITORY_SOURCE 必须是 task 所属仓根/name，同样绑定明确 buildId 的原 commit blob（表达实际 12 本地证据中的维护仓产品源）；TASK_ORIGINAL 的 buildId 必须 null，name 必须在 `doc/tasks/<taskId>/`，路径必须为 task 所属仓根/name，且落在实际 task 内。三类都保留原 path/bytes/SHA，不允许 caller 选一部分成员。repository 参数专供稳定 Git 对象读取，不强制与 task 所属仓根相同。
- 每个本地 pin 精确 `{path,bytes,sha256}`，路径为绝对规范真实路径；报告 pin 必须为 task 直接文件。空原文件允许 bytes=0，报告/归档必须非空。拒绝链接/路径别名及重复/冲突绑定。

输出 `HistoricalBuildCustody/v1` 精确字段：`schemaVersion, taskId, state, inputs, builds, entries, archivePin, installationPerformed, testsExecuted, serverWrites`。state=SEALED，后三项固定 false。builds 保存原报告派生的 `{id,kind,reportPin,sourceCommit,originalWorktree,treeId}`；entries 为按 sets/name 稳定排序的 `{evidencePin,name,purpose,buildId,originalPin,member,blobId,representation}`。TASK_ORIGINAL 的 blobId/representation 为 null；源码 representation 仅 IDENTICAL/CRLF_TO_LF，并真实匹配原 commit blob。

归档 destination 为 private 直属的唯一 `historical-build-custody-<id>` 目录；固定 `inputs.tar` 和 `manifest.json`，O_EXCL，重复拒绝且不清理已有内容。tar 仅允许 `objects/<raw-sha256>` 常规文件，按内容去重；完整成员集合必须与 entries 完全相等。上限：4096 输入、128 报告/构建组、单文件 16 MiB、总 raw 128 MiB、归档 160 MiB、元数据 16 MiB；一次加载只解析归档一次，顺序读取，各输入按报告全核。finish 重新核 manifest/archive/原报告 pins；源码历史验证通过稳定 repository 的原 commit/blob，不读取已删除 worktree。

封存前及末尾核实际专属 worktree HEAD/clean/共同 Git 对象库、原字节和原报告；Git blob 使用单次 batch 读取每代有限命名文件。支持 Git 原 blob 字节或严格 CRLF→LF 表示，未知转换拒绝。封存记录不是安装/测试成功，A 不替代现有安装 checkout 门禁。

## BDD（先于实现）

1. Given 实际提交 LF/CRLF/二进制源码及 task 原日志，When 封存并删除仅测试创建的 worktree，Then 显式 reader 仍返回同一 raw bytes、原 pin 不改、Git blob 关系保持。
2. Given 原报告完整集合，When binding 少项/多项/错 SHA/错路径，Then 封存拒绝且不写 SEALED 结果。
3. Given source checkout 脏或 HEAD 错，When 封存，Then 拒绝；有效旧归档不会让新封存绕过当前 checkout。
4. Given custody 原件，When 缺 archive、错成员集合、重复/链接/穿越/额外成员、超界，Then 读取失败，不能回读仍存在的原文件冒充成功。
5. Given 相同 raw 的两个输入，When 封存，Then archive 只含一个对象，但原报告的两个逻辑引用都严格保留。
6. Given archive 或原报告在 load 后变化，When finish，Then 明确拒绝；伪造 blob/representation 或换 repository 缺原 commit 也拒绝。
7. Given 已存在唯一 destination，When 再次封存，Then 拒绝，已有原件字节不变。
8. Given 未登记 pin/evidence/purpose，When read_original/verify_original_inputs，Then 拒绝，无任意路径 fallback。

## 实际验证命令

仅运行本机新增测试，测试目录由 pytest 临时创建，Git 操作全部限定在其中：

`C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_historical_build_custody.py`

`PYTHONPATH=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies`，`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。本轮实际结果来自下列 exec/session 原终端输出，精确摘要写入本文；未创建另一个声称原始日志的转录文件，不写共享 execution-log。最终完整命令附 `--tb=short`。

## RED / GREEN / REGRESSION

RED A1：按上面命令附 `--tb=line`，`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，原 session 10213 实际终态 exit 1：**32 failed in 12.99s，零 skip**。32 场景均在真实小型 Git/worktree/原报告 fixture 建立后，因 `ModuleNotFoundError: historical_build_custody` 失败；不是 Git 环境或 collect 错误。现在进入最小实现，原业务断言保持。

首次 GREEN 尝试 A1（session 57144）实际 **28 failed / 4 passed，17.94s，exit 1，零 skip**。正式文件保护错误地把 Windows fstat 的 change-time 与 Path.stat 的 creation-time 当同一 ctime；本机新建 3 B 实际文件已复现两者不同，而 birthtime、device/inode/size/mtime 全相同。最小修复仅跨 API 身份比较采用 Windows birthtime，FD 读前后 ctime 仍必须相同，原 SHA 和 inode/大小/mtime 仍完整核验；不改业务测试期望。

GREEN A2：原 session 29360 终态 **32 passed in 38.53s，exit 0，零 skip**。

最终边界 BDD（先测试后修复）：Given 正式完整 tar，When 结束块后追加隐藏非零成员/数据并更新容器 pin，Then 仍须拒绝；Given 实际完整封存即将返回，When manifest 写出后真实 Git HEAD 改变而所选源码字节保持，Then 末尾 checkout guard 必须失败；Given 实际干净 checkout 内恰好有同字节嵌套源码，When 把子目录登记成 worktree，Then 专属 checkout 顶层身份仍必须拒绝。三项仅验证自身临时 Git/文件，没有现场原件。

RED A3：新增三项运行 `-k 'end_blocks or last_seal_guard or top_level'`，实际 **3 failed / 32 deselected in 7.05s，exit 1，零 skip**；三个失败全部 `DID NOT RAISE`，真实复现隐藏尾部、最后 HEAD 漂移、子目录冒充 worktree。现在仅补对应原归档/末尾/root 检查，不改断言。

GREEN A4：原 session 14502 终态 **35 passed in 50.06s，exit 0，零 skip**。

接口完整性 BDD（先于最后实现）：Given 原本地报告包含 task 所属维护仓的产品源码 pin，When 显式 REPOSITORY_SOURCE 封存，Then 原 path 不转换且真实匹配已登记 build commit blob；同 name 改用发布工作区的路径必须拒绝。它只读取该明确原文件，不对维护仓执行 broad status，不扩大为任意路径 fallback。

RED A5：`-k repository_source` 实际 **1 failed / 1 passed / 35 deselected in 3.58s，exit 1，零 skip**。合法维护仓源因旧 purpose 合同被拒绝（SOURCE_PATH_INVALID），错误路径已拒绝。父再次明确认可这个有限 purpose。最小实现只增加固定 task 仓根解析，沿用原报告和 Git blob 全核。

## 最终 GREEN / REGRESSION 与冻结交付

GREEN A6 / 全部 A 回归：原 session 99496 实际终态 **37 passed in 52.74s，exit 0，零 skip、零 deselected**。这是 Windows 上真实小型 Git/worktree、LF/CRLF/blob、原文件、tar 和测试自有 worktree 删除后的验证；不是 Linux/服务器安装/业务备份恢复，也不是实际 461/154 托管。Spy/故障注入仅计数实际 tar 解析或在真实写出 manifest 后改变测试 Git HEAD，没有替换安装成功或原文件读取。

两个 Python 文件均直接 `compile(raw, path, 'exec')` 成功，UTF-8 无 BOM。冻结原件：

| 文件 | bytes | SHA-256 |
| --- | ---: | --- |
| `historical_build_custody.py` | 21646 | `ae9454ee702d9c232179f8a442e890146aa2cd5f3dde3a54c2f5fcd526925369` |
| `test_historical_build_custody.py` | 16653 | `6778998af4b970300d9ad96209821af5c24e1d257749b441fc9cb2c86816e9d0` |

实现没有调用其他 TASK helper；module 导入不读文件。历史 reader 不读原工作区，原逻辑 pin 不改；Git 对象库及原报告必须仍可核验。封存目前仅从明确的现存真实专属 checkout/有限维护仓原件读取，不自动导入旧输入 tar、不支持缺目录 fallback。未声称 B/C 已接入、现有历史读者已能清理后运行或实际归档已完成。

父已确认独立验证本 A 阶段，且现场 Spug 链正在固定共享 helper SHA。本组件已停止扩展，B/C 不启动；没有修改现有 reader、coverage、publisher、runtime 或 cleanup。

## 父独立验证
GREEN: 既定Python -X utf8 -B -m pytest -q -p no:cacheprovider --tb=short test_historical_build_custody.py -> 37 PASS，0 skip，exit0，51.313秒，两个源码输入SHA前后一致。原始日志PRIVATE/historical-build-custody-parent-green-r1.log 102 B / SHAa6846d47a82c5369c6525621e0be609ccb8f481351ad236bba3bf558cb634b0e；报告historical-build-custody-parent-validation-r1.json 1459 B / SHA0a61327b16e1fffc098a87383c1d5e15c1395d2aefcf57bb7cf7f95ed44c0b9a。仅真实临时Git/文件合同，不证明实际461/154封存、B/C接入或清理。
