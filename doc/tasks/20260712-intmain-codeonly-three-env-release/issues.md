# 20260712 IntRuoyi code-only 三环境发布问题记录

## P001 PowerShell 中误用 Bash heredoc

- 现象：读取文档章节时使用 `python -X utf8 - <<'PY'`，PowerShell 解析阶段报 `Missing file specification after redirection operator` 和 `The '<' operator is reserved for future use`。
- 阶段：发布前置经验文档读取。
- 影响：只读文档读取命令失败一次；未创建 worktree，未构建，未发布，未触碰服务器。
- 原因判断：把 Bash heredoc 写法直接用于 PowerShell，不符合本机 PowerShell 规则。
- 处理动作：改用 PowerShell single-quoted here-string 管道到 `python -X utf8 -`。
- 结果：相关文档章节已成功读取，经验门禁已写入任务文档。
- 是否可前置检查：是。
- 是否可自动化：是，PowerShell 命令模板可禁止 `<<'PY'`。
- 下次如何避免：在 PowerShell 下多行 Python/Node 统一使用 UTF-8 临时脚本或 `@'...'@ | python -X utf8 -`，不使用 Bash heredoc。

## P002 配置只读输出包含 NAS 密码字段

- 现象：检查 `config/runtime-control.local.yaml` 时，命令输出包含 `nas-password` 字段及其明文值。
- 阶段：运行控制台配置入口检查。
- 影响：该内容只出现在一次性终端输出中，未写入任务 evidence、任务文档或 Git 提交；后续证据必须脱敏。
- 原因判断：直接打印本地运行控制台配置全文，没有先按 allowlist/脱敏输出。
- 处理动作：停止继续打印原始配置；任务记录仅保留字段名与脱敏说明，最终提交前执行 staged secret scan。
- 结果：未将原始 secret-bearing 输出写入仓库文件；后续配置证据改为结构化脱敏摘要。
- 是否可前置检查：是。
- 是否可自动化：是，配置读取脚本默认过滤 `password`、`token`、`secret`、`key` 等字段。
- 下次如何避免：读取配置前先用脚本生成 allowlist 摘要，不直接输出全文。

## P003 migration policy gate 参数契约漂移

- 现象：执行 `run-release-migration-policy-gate.py --sql-root sql\mysql --json` 返回 exit=2，stderr 显示 `unrecognized arguments: --json`。
- 阶段：build-release 前置门禁。
- 影响：后端迁移策略门禁首次未执行，构建未启动，未发布，未触碰服务器。
- 原因判断：当前后端脚本契约不支持 `--json`，应使用 `--output <path>` 或 stdout；经验文档中的命令形态与当前脚本不一致。
- 处理动作：冻结 stdout/stderr 和 `--help` 输出；更新经验门禁，后续按 `--output` 重跑。
- 结果：待按正确参数重跑；本次 releaseTag 尚未生成。
- 是否可前置检查：是。
- 是否可自动化：是，运行门禁前先执行 `--help` 或脚本参数 introspection。
- 下次如何避免：发布前置命令不能只照历史文档；必须先核对当前冻结 worktree 中脚本真实 `--help`。

## P004 build-release 三环境预览缺 ProdServerHost

- 现象：`build-release` preview 对 `release-20260712-intmain-codeonly-three-env-r260712c-r1` 的参数包含 `-TestServerHost 172.30.30.58` 和 `-BackupServerHost 172.30.30.59`，但缺少 `-ProdServerHost`。
- 阶段：build-release preview 门禁。
- 影响：三环境闭环发布参数不完整；构建未启动，未生成 releaseTag 包，未触碰服务器。
- 原因判断：维护仓 `RuntimeControlOperationAction.buildCommand` 只在 `resolveEnvironment(req)==prod` 时追加 prod host，而 `build-release` 默认环境是 `release`。
- 处理动作：先冻结 preview JSON/raw evidence，再修改维护仓生产代码使 `BUILD_RELEASE` 一律包含三环境 host，并更新 `RuntimeControlContractTest` 覆盖 code-only 和 with-data build-release preview。
- 结果：针对性 Maven 测试通过，维护仓提交 `367786f`，后续必须用新维护仓 HEAD 重新冻结 release worktree 并生成新的 releaseTag。
- 是否可前置检查：是。
- 是否可自动化：是，build-release preview gate 必须断言 `-ProdServerHost`。
- 下次如何避免：三环境闭环进入 build-release 前先结构化检查 `-TestServerHost`、`-ProdServerHost`、`-BackupServerHost`，缺任一项直接 fail fast。

## P005 release worktree 应用前端依赖未恢复

- 现象：`build-release` operation `op-2026-07-13T002006160172900Z-65295a64-bf64-4425-81cf-2e600bafbea0` 失败；日志显示 `pnpm build:test` 缺少 `node_modules`，`cross-env` 不可用。
- 阶段：build-release 后端 Maven 构建成功后，应用前端静态资源构建阶段。
- 影响：`release-20260713-intmain-codeonly-three-env-r260713c-r1` 判废；未生成可发布 Manifest，未执行 publish-test、mark-tested、promote-prod 或 promote-backup，未触碰服务器。
- 原因判断：新建前端 release worktree 后没有先按 lockfile 恢复应用前端依赖；维护控制台自身前端依赖已恢复，但不能代表业务前端依赖。
- 处理动作：冻结 operation JSON 和日志；记录 secret scan 为 0；沉淀前置经验后，在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713c\f` 执行 `pnpm install --frozen-lockfile`，确认 lockfile 不变，再使用新 releaseTag 重建。
- 结果：待依赖恢复并以新 releaseTag r2 重跑。
- 是否可前置检查：是。
- 是否可自动化：是，build-release preview 后、submit 前检查 `frontend/node_modules/.bin/cross-env` 或执行 frozen install。
- 下次如何避免：每个 fresh release worktree 必须分别恢复维护前端和业务前端依赖；不得把维护控制台构建成功等同于业务前端依赖就绪。

## P006 Python subprocess 无法解析 pnpm PowerShell wrapper

- 现象：使用 Python `subprocess.run(['pnpm', ...])` 恢复前端依赖时返回 `FileNotFoundError: [WinError 2]`，但 PowerShell 中 `pnpm --version` 可正常执行。
- 阶段：release worktree 应用前端依赖恢复。
- 影响：依赖恢复首次命令未启动；未修改发布输入、未构建、未发布、未触碰服务器。
- 原因判断：当前 PATH 中优先命中的是 `pnpm.ps1` PowerShell wrapper；Python `subprocess` 在 `shell=False` 下不解析该 wrapper。
- 处理动作：用 `Get-Command pnpm` 和 `where.exe pnpm` 定位 `pnpm.cmd`，改用 `C:\Users\BJB110\AppData\Roaming\npm\pnpm.cmd` 绝对路径执行。
- 结果：`pnpm install --frozen-lockfile` 成功，`node_modules/.bin/cross-env.cmd` 存在，前端 release worktree Git 状态仍 clean。
- 是否可前置检查：是。
- 是否可自动化：是，Windows 上自动选择 `.cmd` 可执行文件或在 PowerShell 原生进程中执行 pnpm。
- 下次如何避免：在 Python/Node 子进程中调用 npm/pnpm/yarn 时优先使用 `.cmd` 入口，并记录实际可执行路径。

## P007 publish-test operation 日志含 MySQL 明文密码参数

- 现象：`publish-test` 失败日志中包含 `mysql -uroot -p<redacted>` 形式的命令参数，初版 secret scan 只匹配 `password=`/`token=`/`secret=`，没有命中该形式。
- 阶段：测试服 `publish-test` 失败证据冻结与日志保存。
- 影响：原始日志不得提交；需要保留脱敏后的失败证据，否则违反日志脱敏门禁。
- 原因判断：发布脚本会把 SSH/MySQL 完整命令写入 operation log；任务侧扫描规则未覆盖无键名的 `-p<secret>` 参数。
- 处理动作：生成 `publish-test-log-r260713c-r2.redacted.json`，删除 `publish-test-log-r260713c-r2.raw.json`，新增增强扫描 `evidence-secret-scan-r260713c-r2.json`，并更新发布日志凭据脱敏门禁。
- 结果：待提交证据 secret-like 命中数为 0，原始秘密日志已从任务证据目录删除。
- 是否可前置检查：是。
- 是否可自动化：是，发布日志保存前统一扫描 `mysql -u... -p<redacted>`、`/user:<user> <redacted>` 等模式。
- 下次如何避免：只保存脱敏 operation 日志；冻结失败证据时同步运行增强 secret scan，命中即删除原始文件。

## P008 required SQL 引用已重命名的路线用途批记录表

- 现象：`publish-test` operation `op-2026-07-13T004825053690400Z-436f346e-5afd-4b88-b5de-be19cf186a6c` 失败；MySQL 报 `ERROR 1146 (42S02) at line 291: Table 'ruoyi-vue-pro.mes_pro_route_use_process_batch_record' doesn't exist`。
- 阶段：测试服 `publish-test` 执行 required SQL `20260708_mes_batch_record_version_phase_one.sql`。
- 影响：`release-20260713-intmain-codeonly-three-env-r260713c-r2` 判废；未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 原因判断：测试服已执行 `20260709_mes_route_flow_config_unification`，旧表被重命名为 `mes_pro_route_use_process_batch_record_legacy_20260709`；但 `20260708_mes_batch_record_version_phase_one.sql` 仍直接对旧表名调用强制加列 helper。
- 处理动作：冻结 operation/failure/db snapshot；沉淀 preflight 经验；按严格 TDD 增加回归测试，修复 SQL 为当前表和 legacy 表双路径 `table exists` 守卫，并提交后端 `fdd93ec98c`。
- 结果：目标测试 `test_mes_batch_record_version_sql.py`、相关 migration metadata/route flow 测试和 migration policy gate 均通过；下一步必须基于新后端提交重新冻结 worktree 并重建新的 releaseTag。
- 是否可前置检查：是。
- 是否可自动化：是，发布前只读检查目标库当前表/legacy 表与迁移状态；静态测试禁止直接对可能已重命名的 legacy 表执行强制 ALTER。
- 下次如何避免：对会被后续迁移重命名的 legacy 表，只允许显式 table-exists 守卫或先声明真实迁移顺序依赖；不得手工改测试库或 migration 状态绕过。

## P009 清理旧 worktree 时进程匹配命中自身 PowerShell

- 现象：清理 `r260713d` 时用命令行包含旧 worktree 路径作为进程匹配条件，当前 PowerShell 命令本身也包含该路径，导致清理命令提前终止且无完整输出。
- 阶段：旧 release worktree 清理。
- 影响：清理首次失败；未删除无关 worktree，未构建，未发布，未触碰服务器。
- 原因判断：进程清理缺少当前进程排除守卫，命中了执行清理的 PowerShell 自身。
- 处理动作：改用 `[System.Diagnostics.Process]::GetCurrentProcess().Id` 获取当前 PID 并排除，只处理命令行包含 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713d` 的其他进程。
- 结果：旧 48181 Java 进程已停止，后续清理继续执行。
- 是否可前置检查：是。
- 是否可自动化：是，所有 worktree 清理脚本固定加入当前进程排除守卫。
- 下次如何避免：清理进程时必须同时限定目标路径、进程类型和当前进程排除；不得只用路径字符串直接 Stop-Process。

## P010 Windows worktree remove 后残留非空目录

- 现象：`git worktree remove --force` 删除 `r260713d\m` 和 `r260713d\f` 时返回 `Directory not empty`；随后检查发现 Git 注册已删除，但物理目录仍残留。
- 阶段：旧 release worktree 清理。
- 影响：旧 worktree 未一次性清理完成；若不处理会阻碍后续判断和 closeout。
- 原因判断：Windows 下深层 `runtime/`、`node_modules/` 或文件句柄会让 Git 注销成功但目录删除失败。
- 处理动作：按 `worktree-memory.md` 门禁确认目标路径在本任务短根内、三仓 worktree 注册均不含 `r260713d`、无其他进程引用后，用受限路径删除残留根目录。
- 结果：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713d` 已不存在，三仓注册均不含该路径。
- 是否可前置检查：是。
- 是否可自动化：是，worktree 清理流程应在 Git remove 后自动检查注册和物理目录双条件。
- 下次如何避免：把 “Git 注册不存在 + 物理目录不存在 + 无进程引用” 作为统一 closeout 门禁，不把 git remove 退出失败或成功单独当最终结论。

## P011 build-release 本地 docker inspect native crash

- 现象：`build-release` operation `op-2026-07-13T020341321200Z-97c25063-2488-4604-aebf-2d62697b2496` 失败；日志显示 `docker.exe : Exception 0xc0000005 ...`，定位到 `publish-int-ruoyi.ps1:1132` 的本地容器 env inspect。
- 阶段：`build-release` 中后端/存储前置检查阶段，尚未生成发布包 Manifest。
- 影响：`release-20260713-intmain-codeonly-three-env-r260713e-r1` 判废；未生成发布包、未执行 publish-test、mark-tested、promote-prod、promote-backup。
- 原因判断：Docker CLI 或 Docker Desktop 对本地容器 env inspect 出现 native crash；随后相同只读 inspect 对必需容器恢复可用，判断为本机 Docker inspect 稳定性/前置健康问题，不是发布包可忽略错误。
- 处理动作：冻结 operation JSON、preview gate、redacted operation log、packageDirMissing；新增 Docker inspect 前置门禁；用白名单方式复核 Docker client/server 可用和本地必需容器存在后，使用新 releaseTag 重建。
- 结果：r1 不继续使用；Docker inspect 前置检查通过，准备 r2 重建。
- 是否可前置检查：是。
- 是否可自动化：是，build-release submit 前自动执行 Docker inspect 状态门禁，失败时不提交 operation。
- 下次如何避免：先核 `docker version`、必需容器存在、inspect 状态命令可用；遇到 `0xc0000005` 必须 fail fast 并重建新 releaseTag，不得继续发布失败包。

## P012 只读排障时打印 Docker 完整 env

- 现象：为复现 P011，直接执行 `docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}'`，终端输出包含本地 MySQL/MinIO 容器环境变量。
- 阶段：build-release 失败排障。
- 影响：原始输出只出现在终端，未写入任务 evidence、任务文档或 Git 提交；后续所有证据必须保持脱敏。
- 原因判断：排障命令没有先做 allowlist/脱敏摘要，违反 secret-bearing 输出最小化原则。
- 处理动作：停止打印完整 env；经验门禁新增 “Docker inspect env 只允许键名存在性或脱敏摘要”；后续 secret scan 覆盖 Docker env、password、token、secret 和 `mysql -p...`。
- 结果：仓库文件未保存该原始输出；后续使用脱敏检查继续。
- 是否可前置检查：是。
- 是否可自动化：是，封装 `docker inspect` 检查脚本默认只输出键名存在性和状态。
- 下次如何避免：任何容器 env 排障先写白名单检查命令，禁止把完整 env 输出贴到任务日志、证据或提交。

## P013 r260713e worktree 残留目录权限拒绝

- 现象：`git worktree remove --force` 对 `r260713e\m` 与 `r260713e\f` 返回 `Directory not empty`，随后物理删除 `r260713e` 因 `remapping` 权限拒绝失败。
- 阶段：旧失效 release worktree 清理。
- 影响：清理完成前不得复用该路径、不得创建新 release worktree 覆盖、不得继续发布。
- 原因判断：Windows 深层依赖目录或文件属性残留导致 Git 注销成功但物理目录删除失败。
- 处理动作：停止旧 48181 Java 进程，确认三仓 Git worktree 注册均不含 `r260713e`、路径位于本任务短根、无外部进程引用；执行 `attrib -R -S -H` 后受限删除。
- 结果：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713e` 物理目录不存在。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：worktree 清理脚本在 Git remove 后必须自动检查注册、物理目录、进程引用和文件属性归一化，不把 Git 注销当作清理完成。

## P014 infra_release_operation_lock 字段名漂移

- 现象：测试服发布前只读锁表预检查询 `updated_time` 失败，MySQL 报 `ERROR 1054 Unknown column 'updated_time'`。
- 阶段：publish-test 前远端只读 preflight。
- 影响：第一次锁表预检无法证明远端发布锁状态；未执行测试服写入。
- 原因判断：真实表字段为 `update_time`，脚本按历史或通用字段名写成 `updated_time`。
- 处理动作：改为先 `SHOW COLUMNS FROM infra_release_operation_lock`，再按实际字段读取锁记录。
- 结果：只读确认测试服锁为 `APPLIED`，当前旧版本为 r260713e-r2，本轮可继续执行 publish-test。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：远端锁表、迁移表、operation 表查询必须先 DESCRIBE 或通过 schema-aware 查询生成，不硬编码未验证字段名。

## P015 mark-tested payload 错传 targetEnvironment

- 现象：`mark-release-tested` 预览首次携带 `targetEnvironment=test`，接口返回 `targetEnvironment`，`body.code=400` 且 `data=null`。
- 阶段：mark-tested 预览。
- 影响：mark-tested 未执行，正式服和备份服 promotion 必须等待。
- 原因判断：运行控制台契约中 mark-tested 不接受 `targetEnvironment`，会从测试服当前 releaseTag 自动解析；同时需要真实 `selectedRecoverySetCandidateId`。
- 处理动作：读取 `/restore-candidates`，使用 `restore:20260621-063218`，移除 `targetEnvironment` 后重新 preview/submit。
- 结果：mark-tested operation `op-2026-07-13T033002346251200Z-4aa4245b-2b17-4979-9e96-f1480a17bfdc` SUCCESS。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：mark-tested payload 门禁固定校验：禁止 `targetEnvironment`，必须包含 `testConclusion` 和来自 `/restore-candidates` 的 `selectedRecoverySetCandidateId`。

## P016 PowerShell 管道污染 Playwright 中文源码

- 现象：通过 PowerShell here-string 管道向 Node 传 Playwright 脚本时，中文正则 `/查看变更/` 被污染成 `/????/`，触发 `SyntaxError: Invalid regular expression`。
- 阶段：运行控制台真实页面版本与变更说明验收。
- 影响：首次 Playwright 脚本未启动浏览器，页面验收未执行。
- 原因判断：PowerShell 文本管道污染 UTF-8 中文源码，符合既有 PowerShell/Node 编码风险。
- 处理动作：把中文选择器与对话框标题改成 Unicode 转义 ASCII 源码后重跑。
- 结果：Playwright 验证测试服、正式服、备份服版本卡片和三个 `版本变更说明` 对话框全部通过，console error=0。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：PowerShell 管道传 Node/Playwright 源码时，中文常量用 Unicode 转义或写 UTF-8 脚本文件并回读校验，不直接在 here-string 中写中文正则。

## P017 PowerShell stdin BOM 污染 Python 脚本

- 现象：PowerShell here-string 管道到 `python -X utf8 -` 时，stdin 首字节出现 `U+FEFF`，Python 报 `SyntaxError: invalid non-printable character U+FEFF`。
- 阶段：复制并改写 release worktree 本地 `runtime-control.local.yaml`。
- 影响：首次配置更新未执行，未改文件、未构建、未发布。
- 原因判断：PowerShell 文本承载层给 stdin 注入 BOM，属于 Windows/PowerShell 编码路径风险。
- 处理动作：改用 `python -X utf8 -c "import sys; exec(sys.stdin.read().lstrip('\\ufeff'))"` 承载脚本，并用后置 health/status 验证。
- 结果：配置写入和运行控制台重启成功。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：PowerShell 管道传 Python/Node 源码统一先剥离 BOM，或改用 UTF-8 临时脚本文件并回读字节。

## P018 runtime-control state-dir 落在 release worktree 导致 dirty

- 现象：48181 指向 `r260713g` 后，维护仓 release worktree 出现 `?? runtime/`。
- 阶段：build-release 前置 clean 检查。
- 影响：若继续 build-release，sourceRepos 可能 dirty 或无法证明构建只来自 HEAD；因此未执行 build-release。
- 原因判断：`runtime-control.local.yaml` 的 `state-dir` 首次指向 release worktree 内 `runtime/state`，控制台运行态写入未跟踪目录。
- 处理动作：停止 `r260713g` 控制台，将 `state-dir` 改到 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g-state`，删除 `m\runtime`，重启并复核三仓 clean。
- 结果：三仓 release worktree clean，后续 build-release manifest dirty=false。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：发布 worktree 的运行控制台 state/log/cache 目录必须放在 Git worktree 外部，或明确列入本地 ignore 且不参与 sourceRepos dirty 判断。

## P019 operation log 再次输出 mysql -p 明文参数

- 现象：publish/promote operation log 中出现 `docker exec ... mysql -uroot -p...` 形式的明文参数。
- 阶段：publish-test / promote-prod / promote-backup 轮询日志保存。
- 影响：原始 operation log 可用于运行态排障，但不得作为任务 evidence 或提交内容保存；本任务保存前进行 redaction。
- 原因判断：发布脚本命令日志仍会记录完整 MySQL CLI 参数。
- 处理动作：本任务 evidence 仅保留 `redacted-tail.log`，将 `-p...` 和 NAS 凭据脱敏；新增 secret scan，提交前不保留 raw secret-bearing 日志。
- 结果：任务文档只记录 operationId、状态和脱敏摘要。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：运行控制台保存 operation log 前应统一脱敏 MySQL/NAS/secret 参数；任务侧提交前必须扫描 `mysql -p`、password、token、secret。

## P020 preview gate 参数解析未兼容单值 flag

- 现象：promote-prod preview 实际包含 `-ServerHost 172.30.30.57`，但本地 gate 用偶数参数配对解析，被 `-RequireTested` 单值 flag 打乱后误判缺 `ServerHost`。
- 阶段：promote-prod preview gate。
- 影响：未执行正式服发布；如果不复核原始 preview，可能误判流程阻塞。
- 原因判断：参数解析器假设所有参数都是 `flag value`，没有处理 boolean/switch flag。
- 处理动作：改用 flag-aware parser，按 flag 查找后继值并单独识别 `-RequireTested`。
- 结果：preview gate 通过，随后正式服 promotion 成功。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：所有发布 preview gate 必须用脚本契约感知解析，不能用简单偶数配对。

## P021 closeout worktree 删除首次失败且无输出

- 现象：收尾脚本首次返回 255 且无 stdout；复核发现维护 worktree 已注销，后端/前端仍需继续清理；前端 `git worktree remove --force` 返回 `Directory not empty`。
- 阶段：release worktree closeout。
- 影响：清理完成前不得标记 completed，不得删除无关 worktree。
- 原因判断：脚本把多步清理串在一个命令中，失败点不够清晰；Windows 前端 node_modules/build 残留导致 Git 注销成功但物理目录未删。
- 处理动作：拆开复核 48181 归属、三仓 Git 注册、物理目录、进程引用；确认路径位于本任务根且无外部进程后删除残留 `r260713g` 和 `r260713g-state`。
- 结果：三仓 Git 注册均不含 `r260713g`，物理目录和 state 目录均不存在。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：worktree cleanup 分阶段记录 stdout/stderr，Git 注册删除后仍必须验证物理目录；残留清理必须限定本任务根并先排除外部进程。
