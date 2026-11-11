# 目标角色配置重建 TDD

## Current Status

ready_for_closeout；实现、纯合同回归和三份真实只读输入的本地重建已通过，待父任务审查并显式提交。不修改服务器、安装状态、旧 all-role 合同或产品执行器；本子任务未提交。

## 目标、里程碑和预期验证

1. RED：先固定可观察 BDD 与单元测试，拒绝角色、主机、原件 pin、官方成员差异、路径和保全图漂移。
2. GREEN：新建 `main_program_target_control_candidate.py`，复用旧规划器绑定函数，仅生成本 target 的不可变配置候选。
3. REGRESSION：新入口单元测试及相邻纯合同回归；读取两个真实官方包验证固定成员差异。真实三服输入由父任务整合，不将静态协议测试写成业务恢复验收。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；所有未知输入明确拒绝。
- 是否从根因和长期维护角度解决：是；明确 target-only 合同承接已独立升级来源，旧147件合同保持。
- 是否存在临时补丁或绕过：否；不重写旧历史、信任、epoch、容量或挂载准入。

## 经验门禁

- Trigger：153件新官方包、目标角色配置重绑定、MAIN 保全图。
- Preflight check：固定旧新包manifest/实际字节/构建提交及显式6新增23改变集合；原owner/control canonical pin；完整14件保全闭包及实际binder字节；仅本target的capture/preservation登记变化。
- Blocker：未知成员或删除、错误pin/schema/角色/主机、路径非规范、保全闭包或epoch改变；失败不输出可安装成功。
- Verification：BDD→RED→GREEN→REGRESSION，命令与原生退出码记录于本文；父任务同步共享execution-log。
- Forbidden action：不放宽旧all-role合同，不写服务器，不授予运行容量/挂载/安装，不从静态PASS推断业务恢复。
- Evidence：父 `main-final-target-upgrade-plan.md`，旧 `package-chain-policy-b5fa4c5-20261110-r1` 和新 `package-main-3fe9dda-r1` 原包。

## BDD

- Given 精确旧目标 controller/owner/control、147→153官方包和完整保全图；When 纯重建单个目标；Then 仅formal/program/PYTHONPATH和本目标capture/preservation引用改变，输出 BOUND_NOT_INSTALLED，保留全部其他原值。
- Given 任一源角色混入、原件或program pin不符、非明确成员差异、构建提交不符；When 重建；Then 明确失败且原输入不变。
- Given 保全图文档pin/闭包/epoch/binder路径或字节漂移；When 重建；Then 拒绝，不补默认或改写源信任。

## 执行证据

- 初始化：UTF-8只读 bootstrap 已读经验索引、PowerShell经验、父目标升级计划；当前只进行本地纯配置工作。
- RED：`python -X utf8 -m pytest -q -p no:cacheprovider --tb=short scripts/tests/test_main_program_target_control_candidate.py` → native exit=1，50 failed in 0.55s，均为 `MISSING_TARGET_ONLY_CONTROL_CANDIDATE`；测试先于实现。
- 只读核两个真实STANDARD包：147→153，明确6新增、23改变、0删除；允许集合写入测试，随后实现固定同组集合，禁止动态批准差异。
- GREEN：同命令 → native exit=0，50 passed in 0.48s。首次发现正则字符串 SyntaxWarning，已改为 raw literal，无业务合同改变。
- 补充 RED：`... pytest ... scripts/tests/test_main_program_target_control_candidate.py -k old-compile` → native exit=1，1 failed/50 deselected in 0.12s；合法AST但不能compile的旧成员未拒绝。最小实现补齐旧包所有Python的compile校验，保持旧planner合同原样。
- REGRESSION：`python -X utf8 -m pytest -q -p no:cacheprovider --tb=short scripts/tests/test_main_program_target_control_candidate.py scripts/tests/test_main_target_preservation_documents.py doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_control_upgrade_plan.py` → native exit=0，101 passed in 13.72s，无警告。包括新54项、保全生成器19项、旧规划器28项；3个附加case重新计算manifest后仍拒绝未批准差异，不能仅靠原manifest拒绝。
- 测试环境：现存独立 `pytest-runtime-8.3.5` / `restore-input-test-deps-20261111`，`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`PYTHONDONTWRITEBYTECODE=1`；PYTHONPATH显式包括任务目录、`ops/recovery`、`ops/backup_engine/formal`。无新增依赖、网络或服务器访问。
- 实际纯重建命令：`python -X utf8 -B C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/verify-target-control-candidate-actual-r1.py` → native exit=0，5.312s；原旧新完整tgz SHA与build报告匹配，三组target均16件新文档、`BOUND_NOT_INSTALLED`，所有输入原字节保持。serverAccess=false、remoteWrites=0、actualBusinessRestore=false。
- 实际私密输出：`C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/actual-target-control-candidates-3fe9dda-r1.private.json`，189303B，SHA256 `8123cd98a12b55d5eac4a27b971db1e67d86df556050e399ccaefb59927e56d3`。只在private保留凭据文档；安全摘要与所有输入pins在同目录 `actual-target-control-candidates-3fe9dda-r1-result.private.json`。
- 入口签名：`build_target_control_candidate(*, host, current_controller, owner, control, package_files, previous_package_files, old_build, new_build, preservation, configuration_root, new_engine)`；返回本target的previousController副本、controller新旧pins、14+2件newDocuments与保持来源配置标记；不会输出激活或容量授权。
- 实现pin：`main_program_target_control_candidate.py`，20306B，SHA256 `fbd6fbf65643cbb94669c2f69ce07b7a084a2933b9b753880ad12e2cfaa332cd`。测试pin：`test_main_program_target_control_candidate.py`，20669B，SHA256 `c0c21605962b7b3bacdbe557de6230f3cc2de37b341036fa1163bb61acdd36ba`。
- 本任务3文件UTF-8无BOM回读与Python compile通过；`git diff --check`通过。仅本任务3个新文件；旧planner、产品和服务器未修改。
- 收口复核：本任务3个未跟踪文件单独UTF-8与行尾空白检查PASS；全仓 `git diff --check`另报告父任务正在编辑的 `execution-log.md:3037`、`docs/request-command-log.md:6298` EOF空行。本子任务不修改共享日志，已报父任务处理；不将全仓检查写成全部PASS。
