# Spug 只读 bind 发布续办：BDD / TDD

## Current Status

ready_for_closeout（本机实施阶段）。本轮父任务已批准 `spug-readonly-bind-publication-design.md`（批准时 SHA256 `c071925d508f8deeee088c55d25e9222e2f75128b7b4c79c48b236838bdacba5`）及三个最小 reader 接缝。本机实现与必要回归已通过并冻结；父独立验证、实际续办及提交尚未执行。本阶段只修改本任务工具/新测试，没有执行 Docker、服务器、构建、运行配置发布或 Git 提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。精确存储分类；未知状态即停止。
- 是否从根因和长期维护角度解决：是。独立 v3 发布尝试承接原 v2 失败，保持只读挂载和控制代次。
- 是否存在临时补丁或绕过：否。原发布程序正文和旧 v2 publisher 保留，完整 reader 深校验共用。

## 经验门禁

- Trigger：原容器 ro bind 导致部分发布停在配置首写。
- Preflight check：设计中的原 FAILED/八阶段/r2/mount/runner 终态、同代资源和全七项 custody。
- Blocker：缺真实原件、路径或状态歧义、已有尝试、任一局部未知写入。
- Verification：本机真实文件/子进程 RED→GREEN→受影响回归；现场另由父验证。
- Forbidden action：不改挂载、不重跑 host-publish、不覆盖旧原件、不自动重试、不用 fixture 充当部署成功。
- Evidence：本日志、私密独占原始测试输出和源码 pins、父任务实际原件。

## BDD

1. Given 七个原计划目标，When 明确 mount 分类，Then 原顺序为四个 HOST_BIND、两个 CONTAINER_VOLUME、最后 HOST_BIND，未知路径/mount 拒绝。
2. Given 真实临时磁盘原文件与 custody，When 原子替换，Then 原字节先保全，新字节实际读回；新文件抢占/别名/custody 漂移拒绝。
3. Given 任一 custody 尚未完成，When 发布批次，Then 没有运行目标写入；替换后回执失败保留实际新字节并停止，不能重试。
4. Given 原七个 PASS 加第八个 FAILED，When 新明确 continuation，Then 原件全部保持且 host 只 verify；缺项、未知结果、改代次或换 ID 重派拒绝。
5. Given 真实原生结果和原容器读回，When 最终严格 reader，Then 三来源×三目标、33 apps/3 tasks、历史路径及全部保护通过才可投影 core；bool-only 不足。

## 测试边界

新增 fixture 是本机合同测试，不是现场安装。磁盘原子变更、保全和失败后内容使用真实临时文件。外部传输只记录协议/拒绝派发，不把返回 fixture 称作实际部署。原 v1/v2 测试及断言保持。

## RED

所有命令使用指定缓存 Python、`-X utf8 -B -m pytest -q -p no:cacheprovider`，`PYTHONPATH=PRIVATE/test-dependencies`、`PYTHONDONTWRITEBYTECODE=1`。测试文件为 `TASK/test_main_program_spug_publication_continuation.py`。下表日志均位于本任务 PRIVATE，保留原失败，没有覆盖。

| 阶段/日志 | 真实结果 | SHA256 |
| --- | --- | --- |
| `readonly-bind-red-r1.log` | 21 failed，exit1，模块接口缺失 | `d879d165615e005eef7ef4e91b78638245e5e818094eacc1420ff0291bf2e1a7` |
| `readonly-bind-green-files-r1.log` | 21 passed，0.50s，exit0 | `de7a0f127bf2cf40c2c04a68b258e055fdf72a66f5cad6e736ed175a058e7d64` |
| `readonly-bind-red-records-r1.log` | 11 failed / 21 passed，exit1，原失败/mount/custody reader 缺失 | `db4a5f679111868a0ba6b5dabacb5a39d2ca0f3cbb20b9f0d923a7b7b86ad69d` |
| `readonly-bind-green-records-r1.log` | 1 failed / 31 passed，exit1，真实 inspect 与投影列表顺序不同；按 Destination 精确排序核相同集合，未放宽 mount 字段 | `7ca5e22f561de6e51e9298c5f0d5824906039e8bb0b74d1dbd868c6a7b2750a5` |
| `readonly-bind-green-records-r2.log` | 32 passed，0.58s，exit0 | `45415e89d4e3b349b15b5383ad58f4d9c31be6c0ff1e6b0f6d9db2fecd43a548` |
| `readonly-bind-red-source-custody-r1.log` | 6 failed，exit1，旧源码托管缺失；`-k historical_source` | `32b41199b9712b3a6086b3e156c78cf0831df1f819fab4b15f2143fe24387f9e` |
| `readonly-bind-red-shared-reader-r1.log` | 1 failed / 38 passed，exit1，共用深校验接缝缺失 | `2e363a1e5652949e230ac1b04520126ccccec65b156cb2ada89a0dd56db68772` |
| `readonly-bind-green-shared-reader-r1.log` | 39 passed，0.57s，exit0 | `603668fbea5fa8439b921c025fcec0114f3d6c77035fb89e35070c1c18df2dd2` |
| `readonly-bind-red-batch-r1.log` | 2 failed，exit1，全保全屏障/实际替换后回执失败批次函数缺失；`-k real_batch` | `5aa4c0f5be6a37afceb2bbec0d8d7ac0a8276a55d4d6329200c8154c0cda6207` |
| `readonly-bind-green-real-prepare-r1.log` | 42 passed，4.68s，exit0，包括正式 c1 的真实本机 prepare | `0e9fc232b3a5550993798b9d95fbbe5e2d27785ae714aac0276c70edea6000c1` |
| `readonly-bind-red-native-custody-r1.log` | 1 failed / 47 passed，exit1，container custody 深绑定缺失；真实原生进程非零/损坏输出/超时测试已通过 | `2b0fd14f0643a10485369a22d1a41e2407f7732f0978000114b579d5e905f303` |
| `readonly-bind-red-entry-guard-r1.log` | 1 failed / 1 passed，exit1；真实宿主文件被改，暴露 entry 写前 guard 缺失；host custody decode 方法已实际通过 | `d3cc59bdc8ab14b00e62226a6b92721f0fb86774218575044f72a49436ad1578` |
| `readonly-bind-red-argv-selection-r1.log` | 2 failed / 53 passed，exit1，SSH 可执行文件不精确及 v3 分派缺失 | `2dda826245cfe7f671edf5a792fc70b2d6b15223e4542b83dfcb619c77e263b9` |
| `readonly-bind-green-execution-r1.log` | 55 passed，9.59s，exit0 | `c366df014bf77046be34b0dc85ed07108702474711d3380723b9263ad6d6e329` |
| `readonly-bind-full-orchestration-r1.log` | 1 passed，3.00s，exit0；`-k full_local`，真实七文件写入后协议明确拒绝外部验证，产生 FAILED、无 core，非现场成功 | `78a2e1a14531f560518e33f08b196a98063131a300dc521115c274b598f57cc3` |

正式 c1 初次直接调用纯 prepare 实际拒绝 `CONTINUATION_ORIGINAL_DISPATCH_CHANGED`（工具会话 exit1、3.59s）：旧 request.host 是完整 IP，而本地新 reader 初稿误按 suffix。依实际原件纠正后，42项 GREEN 包含同一完整纯 prepare，不改任何旧 request/program。

## 源码保全与闭包

实施前已排他保存四个源码到 `PRIVATE/readonly-bind-baseline-<原文件名>.private`。publication 原 SHA `ec4ca9f834332ef3b235c731f401b1c6435a49f08d2117be1acce1c35616aaae`，v2 publisher 原 SHA `0915b324db982f1213289a35a8148833f69c141fa080d91671fee00696eb37fa`，selection 原 SHA `f663ab53ae810b115fb418062e162d0a592349d7081fb59adcf191d5e4488966`，collector 原 SHA `61d320d245c000c19c692d57a9e5cf15c257b38f411b36c72084d1889825f7a4`。

旧286输入的两个已变化 reader 通过父正式 source custody 证明原字节，其余输入逐 pin 复核；新执行源码另固定。运行配置 before 不进入要求永久不变的源码闭包，由旧状态原件和全七项 custody 证明。真实 pure prepare 逐字节重建比较原八个生成程序，证明原 HOST/SPUG 正文和嵌入 guard 未缩减。

## 回归与现场限制

原测试没有改断言。新增测试不调用 Docker/服务器；容器 payload 在本机编译，内部文件原子 helper 与宿主 custody 方法在真实临时文件上执行。Linux `/proc`、只读 mount 与完整嵌入程序的实际验收由父在明确隔离容器和后续原容器只读 guard 中完成，本机测试不冒充该验收。

| 阶段/日志 | 真实结果 | SHA256 |
| --- | --- | --- |
| `readonly-bind-regression-r1.log` | 390 passed / 0 skipped，152.46s，exit0；原输入保持 | `a0928401d3c7a9b1b9fa63e4198579923b7d43b1c87ad060f98614dbb0d35d90` |
| `readonly-bind-red-custody-destination-r1.log` | 1 failed / 1 passed / 55 deselected，0.66s，exit1；错误归档路径未在首写前拒绝 | `4fe7d4c5b9251ad8308757b29837136a13e96a4ff085ca491a55efb29ab94494` |
| `readonly-bind-regression-r2.log` | 391 passed / 0 skipped，201.21s，exit0；12 份源码/测试前后 SHA 全部保持 | `ef7fec70a7f53d8c2408c55b17acdca8be1abed59c0d52f30745c8dc2b3e5c82` |

最后修复只在 `prepare_custody` 返回前调用已有 `validate_container_custody`，让容器归档路径和原字节对应关系在运行文件首写前完成严格核对。原失败日志保留。最终回归原会话已真实终态，完整命令和退出码存于 `PRIVATE/readonly-bind-regression-r2.private.json`。

回归命令（工作目录为本任务开发 checkout；指定上述 Python 和环境）：

```text
python.exe -X utf8 -B -m pytest -q --tb=short -p no:cacheprovider TASK/test_main_program_spug_publication_continuation.py TASK/test_main_program_spug_publisher_v2.py TASK/test_main_program_publication_v2.py TASK/test_main_program_spug_publication.py TASK/test_main_program_installation_selection.py TASK/test_closeout_host_snapshot.py TASK/test_main_program_control_generation.py
```

这里 `TASK/` 仅为文档缩写；实际 argv 使用 `doc/tasks/20261106-spug-prod-incremental-to-two-targets/`。7 模块覆盖新续办 57 项与原发布器/reader/选择/收尾/代次回归。

## 冻结交接

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `main_program_spug_publication_continuation.py` | 61369 | `2a4be50c1592edc561673f5771a16def5bc38044e2a1c17c3ef232e08a969dc1` |
| `test_main_program_spug_publication_continuation.py` | 25677 | `70cb36c12db98297962493be5ea6f3bace8f7845740903e8615ab600a6300b37` |
| `main_program_spug_publication.py` | 83007 | `01077433077cda8a44619215fc234a40240b7a013ab880e4c334622b88dde740` |
| `main_program_installation_selection.py` | 14854 | `d1191685c5792f3caf438d0b093285ded09800140677db4b71b7e089332cbe0b` |
| `observe_closeout_hosts.py` | 16472 | `d62693e5c241e56602f9106896bea7f49da717e10dfc50631211b1348bb34c85` |

另外交付本日志与设计文档。5 份源码/测试已无 pyc 编译检查；三个接缝 `git diff --check` exit0。原 `HOST_BODY` / `SPUG_BODY` AST 字符串逐字节相同，旧 v2 publisher 全文件原字节相同，原旧测试文件未修改。差异原件为 `PRIVATE/readonly-bind-reader-review-r1.diff`（8938B，SHA256 `6ba399e60e68a4737f05adc39be8084bf37334a4831b9e7ea1cc117d8b67a471`）。完整冻结 pins 和原始日志 pins 另独占写入 `PRIVATE/readonly-bind-freeze-r1.private.json`。

### 父任务调用接口

- 纯准备：`prepare_continuation(task, private, inputs_file)` 或 CLI `main_program_spug_publication_continuation.py --inputs main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json`。默认不派发，返回 `PREPARED_NOT_APPLIED`。
- 原容器只读 guard 载体：`container_program(prepared, 'guard-before-custody')`。核 entry 身份、原空 audit、7 项原状态及新 audit 不存在；不创建 audit 或修改运行配置。
- 隔离容器文件合同载体：`container_program(prepared, 'custody')`、`container_program(prepared, 'write', 4)` / `5`、`container_program(prepared, 'readback', i)`。这些是实际嵌入程序；父需给与合同一致的隔离 fixture，不能将 fixture 结果当真实发布。
- 真实续办仅由父在独立验证完成后显式 CLI `--apply`；本阶段未调用。所有 7 项 custody 完整验证后才首写，原顺序四个 bind → 两个 volume → bridge；原 3 个 host 仅 verify。

新输出 stem 固定 `main-program-spug-installation-45dd7dc-r6-continuation-c1`：TASK 下 `<stem>.json` 仅实际成功；PRIVATE 下 `<stem>.attempt.private.json`、`<stem>.private.json`，以及逐 stage / native receipt / 七项 write 状态原件。若 rich 已写后本地 finalization 失败，另写 `<stem>.finalization-failure.private.json`，不覆盖旧原件。容器新 audit 为 `/var/lib/intruoyi-spug/publication-main-program-45dd7dc-r6-continuation-c1`，原 r6 audit 保留。

每项 bind 写前执行精确 entry / audit / 当前七状态只读 guard；所有 7 次容器 readback 与 2 次 volume write 均由原生 argv、program、退出码和 stdout 深绑定，不能仅保留 inspect 或布尔声明。未知写入立即停止，持久排他 claim 保留，不删除 gate、不自动重试或回滚。原失败、八阶段、原 286 输入与原源码正式托管全保留。

仍待父完成：独立本机回归与正式 c1 pure prepare、原容器只读 guard、隔离 Linux 完整嵌入体合同、实际续办及真实 UI 矩阵。这里只确认本机合同 GREEN，不宣称发布或用户目标已完成。
