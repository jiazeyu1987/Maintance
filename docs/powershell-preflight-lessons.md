# PowerShell 事前经验清单

## 门禁摘要

- Trigger: Windows PowerShell 5.1、中文文本、here-string、管道、SSH、MySQL、外部命令退出码或运行控制台脚本任务。
- Preflight check: 先读取权威共同规则 `E:\IntRuoyi\docs\powershell-memory.md`，再读取本文的维护仓专项增量；设置 UTF-8 编码并设计后置断言。
- Blocker: 共同规则未读取、中文编码链路不明确、命令依赖 `&&`、只看 stderr 或进程退出而没有结果断言。
- Verification: UTF-8 回读、`$LASTEXITCODE`、结构化响应、目标文件/数据库/远端状态后置校验。
- Forbidden action: 不得把本文当作另一套共同 PowerShell 标准，不得用管道乱码、静默 warning 或默认编码继续长链路操作。
- Evidence: 命令、stdout/stderr、字节或文本回读、任务 execution-log 和目标状态断言。

## 适用范围

当任务涉及 Windows PowerShell 5.1 命令执行、脚本排查、中文文件读取、中文日志输出或多条命令串联时，先读本文。

PowerShell 共同基础规则以 `E:\IntRuoyi\docs\powershell-memory.md` 为唯一权威来源；本文只沉淀维护仓、运行控制台和构建发布专项增量。若文字重复，以共同规则为准；维护仓更严格的专项门禁继续叠加执行。具体业务发布、备份、恢复和 E2E 规则仍以对应业务文档为准。

启动时允许且只允许一条固定的只读 bootstrap 命令：先设置 UTF-8，仅用于读取适用的 `AGENTS.md`、上一任务状态、经验索引和 `powershell-memory.md`。该 bootstrap 是 task-doc-first 的唯一前置例外；不得写文件、调用外部服务、执行构建/测试/发布或通过管道传递业务文本；完成读取后必须立即创建或更新任务文档并摘取经验门禁，后续 PowerShell 命令全部按权威共同规则执行。

## 必做预检

1. 不使用 `&&`。
   - PowerShell 5.1 不支持 `cmd1 && cmd2` 这种串联方式。
   - 需要连续执行多条命令时，改用分行执行，或使用 `;` 连接。
   - 在维护仓、业务仓、侧边聊天和执行脚本里都按这个规则处理。

2. 中文读写必须显式 UTF-8。
   - 读取中文 Markdown、JSON、SQL、日志、任务文档和 `AGENTS.md` 时，使用 `Get-Content -Encoding utf8`，或改用 `python -X utf8` 等 UTF-8 感知运行时。
   - 不要直接用默认 `Get-Content` 读取 UTF-8 无 BOM 中文文件，避免乱码或误判内容。

3. 中文写入优先不用 PowerShell 默认输出。
   - 不用默认 `Set-Content`、`Add-Content`、`Out-File`、`>`、`>>` 去写中文内容。
   - 优先用 `apply_patch`；若必须通过脚本写入，显式指定 UTF-8，无 BOM 优先，并在写后重新按 UTF-8 回读校验。

4. 终端输出中文前先设编码。
   - 命令输出、日志采集或脚本诊断包含中文时，先设置：
   - `[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)`
   - `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`
   - `$OutputEncoding = [System.Text.UTF8Encoding]::new($false)`
   - `chcp 65001` 只能当会话辅助，不能替代显式编码设置。

## 快速判废信号

- 命令里出现 `&&`，直接改写后再执行。
- 中文文件用默认 `Get-Content`/`Set-Content`/重定向处理，直接判定为编码风险。
- 中文日志、SQL 结果或任务文档出现乱码，先停下确认编码，不继续连锁操作。

## 本次沉淀

- 侧边聊天和主线程共用同一台 Windows 机器，PowerShell 5.1 限制一致；侧边聊天里同样不能写 `&&`。
- 侧边聊天虽然常用于轻量探索，但只要涉及中文文件读取或命令输出，也必须沿用显式 UTF-8 规则，不能因为“只是看一下”就省略编码门禁。

## 2026-07-10 PowerShell 向 Python/Node 管道传源码的编码门禁

- 将包含中文源码的 PowerShell here-string 直接管道给 `python -` 或 `node -`，可能在解析前变成 `?`，造成正则表达式语法错误、字符串比较失败或证据 JSON 写入乱码。
- 优先方案：脚本源码保持 ASCII，中文常量使用 `\uXXXX`；或将 UTF-8 无 BOM 脚本文件写到受控临时目录后直接执行，并在写后按 UTF-8 回读。
- `$OutputEncoding`、`[Console]::InputEncoding`、`[Console]::OutputEncoding` 必须设置，但不能替代对管道源字节的验证。
- 发现 `????`、中文比较明明相同却失败或 JSON 中文字段乱码时，必须停下重生成证据，禁止继续沿用损坏文件。

## 2026-07-10 Windows subprocess 向 SSH bash 标准输入必须禁用 CRLF 转换

- Trigger: Windows 上通过 Python subprocess、PowerShell 或其他客户端把多行脚本送入 SSH 远端 `bash -s`。
- Preflight check: 发送前将脚本编码为 UTF-8 bytes，并断言输入字节不含 `\r`；禁止使用可能自动转换换行的 `text=True, input=script`。
- Blocker: 输入含 CRLF；远端 stderr 出现 `set: -\r invalid option`、路径尾部 `\r`、`do\r` 或等价语法错误。
- Verification: 使用 `input=script.encode('utf-8')` 发送，stdout/stderr 显式 UTF-8 decode，远端命令退出码为 0 且关键输出完整。
- Forbidden action: 不得把远端脚本因 CRLF 未执行误判为服务器、Docker、数据库或业务数据异常，不得继续复用损坏脚本输出。
- Evidence: `doc/tasks/20260710-current-head-test-only-release-completion-audit/execution-log.md`；首次 text 模式失败，改为 UTF-8 bytes + LF 后同一只读验证通过。
- 2026-07-31 追加证据：`release-20260731-smartseed-tempfix-head-test-r260731d-r1` 发布后验收首次用 `text=True` 发送 SSH stdin，stderr 出现 CRLF 解析错误且 `.env IMAGE_TAG` / frontend inspect 证据不完整；改用 `input=remote_script.encode('utf-8')` 后同一远端验收完整通过。

- 推荐写法：`input=script.encode('utf-8')`，按 bytes 发送；stdout/stderr 再显式 `decode('utf-8', errors='replace')`。
- 失败时保留 stderr 和输入换行检查结果，再修正传输层；不要先改远端命令或环境。

## 2026-07-10 原生命令 stderr 与 PowerShell 自动变量门禁

- `git checkout` 等原生命令可能在成功且退出码为 0 时向 stderr 输出正常提示；`$ErrorActionPreference='Stop'` 不能代替 `$LASTEXITCODE` 判断。
- 需要可靠捕获时使用 `Start-Process -Wait -PassThru` 配合 stdout/stderr 文件，并以 `ExitCode` 为准；正常 stderr 作为证据记录，不直接判失败。
- PowerShell 变量后紧跟冒号时使用 `${Path}:`，避免 `$Path:` 解析错误。
- 不把函数参数命名为 `$Args`；它是 PowerShell 自动变量，容易造成数组绑定和参数读取异常。

## 2026-07-10 HTTP 健康检查与进程路径扫描门禁

- `Invoke-WebRequest.Content` 在不同 PowerShell/HTTP 响应组合下可能是 `byte[]`，不得直接使用 `-match 'UP'`；JSON 健康接口优先用 `Invoke-RestMethod` 并断言结构化 `status`。
- 若必须使用 `Invoke-WebRequest`，先按响应编码将字节显式解码，再做字符串或 JSON 判断。
- 按命令行扫描占用某个 worktree 的进程时，清理命令自身也会包含目标路径；必须排除当前 `$PID`，再检查剩余进程，避免把执行壳误判为外部锁定进程。

## 2026-07-11 PowerShell/SSH/Playwright 发布验收门禁

### Trigger

PowerShell 5.1/7 中执行 SSH、bash 片段、HTTP host:port、release-info JSON、Playwright 页面验收或含中文发布说明的命令。

### Preflight check

- PowerShell 字符串中变量后紧跟 `:` 时必须写 `${var}`，例如 `http://${hostIp}:8081/`。
- bash 片段含 `$()`、`$var`、`||`、管道或引号时，不放入 PowerShell 双引号；优先用 UTF-8 文件、单引号字符串或逐条短命令。
- 远端脚本启用 `set -u` 时，所有本地变量必须显式传入远端变量名，不得直接引用本地 PowerShell 变量名。
- SSH 多行输出前先跑一条只读探针；OpenSSH `IO is still pending on closed socket` 只能作为 SSH 采集问题处理，不得覆盖应用实际 health/HTTP 结果。
- Playwright 前先执行 `node -e "require.resolve('playwright')"` 并确认浏览器 executable path；缓存缺失时使用已安装 Chrome/Edge，发布验收中不临时下载浏览器。
- release-info 中文内容用 UTF-8-aware parser 或真实浏览器核验；PowerShell 默认对象渲染出现 mojibake 时不得作为失败或通过的唯一依据。

### Blocker

- URI 被插值成 `http:///`、远端脚本变量未绑定、bash 被 PowerShell 本地解析、Playwright 模块/浏览器不可用且没有稳定替代路径。
- 命令输出可能包含 secret 值且尚未经过 allowlist/redaction。

### Verification

- 记录实际 URI、SSH 退出码、HTTP status、health JSON、Playwright result JSON 和截图路径；敏感值只记录字段名或脱敏结果。

### Forbidden action

- 禁止打印完整 runtime-env、`.env`、secret key、password、token 或私钥内容。
- 禁止用接口直读替代用户明确要求的真实页面/版本对话框验收。

### Evidence

- `20260711-current-head-test-only-release` P020-P028。
- 2026-08-01 追加证据：`doc/tasks/20260801-head-test-only-release/execution-log.md` 的只读远端复核中，SSH exit code=`0` 且 `.env`、容器、health、HTTP、lock/migration 必需字段完整，但 stderr 出现 `close - IO is still pending on closed socket`；本类 warning 只能作为 carrier 分层记录，不能覆盖完整 stdout 里的业务状态。

## 2026-07-12 PowerShell 自动变量与进程守卫门禁

- Trigger: PowerShell 脚本中定义变量、函数参数、进程扫描或 worktree 删除前置检查。
- Preflight check: 避免使用 `$PID`、`$Args`、`$Host` 等自动变量名作为自定义变量；扫描命令行占用时排除当前进程 ID，并排除当前检查脚本自身的命令行。
- Blocker: 变量名与自动变量冲突、进程列表只命中当前清理脚本、无法证明真实外部进程未占用待删 worktree。
- Verification: 记录进程扫描过滤条件、剩余匹配进程数量、worktree 注册和物理路径结果。
- Forbidden action: 禁止因当前检查命令包含目标路径就误判外部进程占用；禁止在未确认路径边界和进程引用前递归删除。
- Evidence: `doc/tasks/20260712-current-head-test-only-release/issues.md` P009、P018。

## 2026-07-12 native 命令 stderr 与退出码门禁

- Trigger: PowerShell 执行 pnpm、git、docker、ssh、maven 等 native 命令并采集 stdout/stderr。
- Preflight check: 以 `$LASTEXITCODE` 或进程 `ExitCode` 为准；stderr 必须结合退出码和产物存在性判断，不能单独判失败。
- Blocker: native 命令退出码非 0、产物缺失、stderr 表示真实错误且无通过证据。
- Verification: 记录命令、退出码、关键 stderr 摘要和产物/manifest 校验结果。
- Forbidden action: 禁止把成功命令的普通 warning/stderr 当作失败；也禁止忽略非 0 退出码继续发布。
- Evidence: `doc/tasks/20260712-current-head-test-only-release/issues.md` P010。

## 2026-07-13 PowerShell 发布脚本承载、参数解析与证据脱敏门禁

- Trigger: PowerShell 中执行发布 API 辅助脚本、`python -c`、Python/Node stdin、Playwright 脚本、`rg` 正则检查、运行控制台 preview 参数校验或发布日志脱敏。
- Preflight check: 多行 Python/Node 不使用 Bash heredoc，也不把带 `\n` 的多行源码压进 `python -c`；stdin 执行时先处理可能出现的 `U+FEFF`；中文按钮文案、中文正则和 Playwright 选择器优先使用 Unicode 转义或 UTF-8 脚本文件；解析 preview 参数时按 flag 查找下一项，不能简单两两配对；`rg` 搜索以 `-` 开头的正则时加 `--`，需要 lookaround 时改用 Python 或 `rg --pcre2`；脱敏规则必须区分真实 secret 与普通参数/路径。
- Blocker: 出现 `Missing file specification after redirection operator`、`unexpected character after line continuation character`、`invalid non-printable character U+FEFF`、中文正则变成 `????`、preview 因单值 flag 错位误判目标 host、`rg` 把正则当 flag、默认 `rg` 不支持 lookaround、脱敏把 `-ProdServerHost` 或 `ruoyi-vue-pro` 当成密码。
- Verification: 执行后保存结构化 preview gate、脚本退出码、UTF-8 回读结果、Playwright 页面结果、脱敏前后扫描摘要；参数 gate 必须证明 `-ServerHost`、`-ReleaseTag`、`-RequireTested`、`-ConfirmText` 等关键 flag 各自命中正确值。
- Forbidden action: 不得在 PowerShell 里直接使用 Bash heredoc；不得只靠设置 `$OutputEncoding` 就认为 stdin 中文不会污染；不得用 `args[0::2]`/`args[1::2]` 解析含无值 flag 的命令；不得用过宽脱敏正则污染 releaseTag、仓库名、host 参数或数据库名；不得把脱敏后的误伤日志当作真实远端命令证据。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/execution-log.md`；主线程遇到 `python -c` 换行语法错误、stdin `U+FEFF`、Playwright 中文正则污染、promote-prod preview flag 错位误判、`rg` 正则 flag/lookaround 问题，以及 `mysql -p...` 脱敏规则误伤 `ruoyi-vue-pro`。
- 2026-07-29 追加证据：本机 `npx playwright install chromium` 超过 300 秒未完成，但稳定安装的 Chrome 可通过 `npx playwright screenshot --channel chrome ...` 和 `npx playwright cli open --browser chrome ...` 完成测试服前端与运行控制台版本对话框验收。日志脱敏正则必须只匹配空白后的 CLI 参数 `\s-p...`，避免把普通库名 `ruoyi-vue-pro` 误改成脱敏文本。2026-08-01 追加证据：`doc/tasks/20260801-head-test-only-release/publish-test-operation-r260801a-r2.sanitized.log` 保留 `ruoyi-vue-pro` 数据库名，只脱敏 `mysql -p<secret>` 形态；脱敏后必须再做 secret pattern scan 与普通名称保真检查。

### 推荐做法

- 多行 Python：`@' ... '@ | python -X utf8 -c "import sys; exec(sys.stdin.read().lstrip('\ufeff'))"`；若脚本含中文关键字，优先写入 UTF-8 临时脚本文件并回读。
- Preview 参数：实现 `value_after(flag)` 或等价解析；对 `-RequireTested` 这类无值 flag 用包含检查，对 `-ServerHost` 这类有值 flag 用“flag 后一项”等值检查。
- `rg`：正则以 `-` 开头时使用 `rg -- "<pattern>" <path>`；包含 lookahead/lookbehind 时使用 `rg --pcre2` 或 Python `re`。
- 脱敏：只匹配 `mysql -p<非空密码>`、`/user:<user> <secret>`、`password/token/secret` 等明确 secret 形态；扫描命中后打印上下文人工确认，避免把 `-ProdServerHost`、`ruoyi-vue-pro`、releaseTag 或普通路径改写掉。


## 2026-07-13 Playwright console 统计文本与 release-info CRLF 门禁

- Trigger: PowerShell/Playwright/SSH 组合采集运行控制台页面、console 输出或远端 `release-info.json`。
- Preflight check: `release-info` 使用 JSON parser 或 CRLF-safe compact；Playwright console 输出以错误计数结构化判定，不用 `contains("error")` 扫描整段工具输出。
- Blocker: CRLF 导致 release-info 字段截断、`Errors: 0`/`Warnings: 0` 被当成真实错误、PowerShell byte[] 或默认渲染导致中文/JSON 证据不可读。
- Verification: 证据中 releaseTag 与 source commit 均匹配；console result 明确 Total messages 与 Errors/Warnings 计数；页面版本号与变更说明可见。
- Forbidden action: 不得用 HTTP 200 或页面可打开替代版本/变更说明验收；不得将解析器误判通过手工标绿。
- Evidence: `doc/tasks/20260713-current-head-codeonly-three-env-rerun/execution-log.md` 的 `release-info-crlf-parser` 与 `console-error-string-parser`。

## 2026-07-14 远端验收工具可用性门禁

- Trigger: Windows 本机通过 SSH 在测试服、正式服或备份服执行发布后验收脚本，脚本需要解析 `.env`、Docker 镜像、health、HTTP、PDF worker、`release-info.json`、release lock 或 migration 状态。
- Preflight check: 远端脚本不得默认目标机存在 `python3`、`jq`、`node` 等解析工具；若计划使用这些工具，先执行 `command -v <tool>` 并把工具可用性作为显式断言。通用发布验收优先使用 POSIX shell、`grep`、`sed`、`awk`、`curl`、`docker` 和 MySQL heredoc 等目标机已确认能力。
- Blocker: `python3: command not found`、`jq: command not found`、工具预检失败、SSH 在业务断言前退出，或无法证明远端是否执行过发布状态检查。
- Verification: 失败证据必须区分 carrier/tooling 失败与服务器运行态失败；改写后记录 SSH exit code、`.env IMAGE_TAG`、backend/frontend image tag、backend health、frontend HTTP、PDF worker HTTP、release-info、release lock 和 migration failed count 的结构化断言。
- Forbidden action: 不得把远端工具缺失当作发布失败或发布成功；不得因此跳过 release-info、release lock、migration 或 PDF worker 核验。
- Evidence: `doc/tasks/20260713-current-head-codeonly-three-env-r260713v/execution-log.md` 的 `backup-runtime-verification-python3` 与 `backup-runtime-verification`。

## 2026-07-13 SSH stdin、Windows 二进制 LF 与远端 SQL 验收门禁

- Trigger: Windows 本机通过 Python/PowerShell 调 `ssh ... bash -s` 发送多行远端验收脚本，或通过 SSH 查询远端 MySQL 发布锁、migration 状态、`.env`、compose 与 release-info。
- Preflight check: 需要向远端 `bash -s` 传 stdin 时禁止使用 `ssh -n`；Windows Python `subprocess` 不使用 `text=True` 传远端 bash 脚本，改用 `input=script.encode('utf-8')` 并确认 LF；远端 SQL 核验优先用 `docker exec -i ... mysql <<'SQL'` heredoc 和单引号 SQL 字面量。
- Blocker: 输出为空但断言全失败、stderr 出现 `set: -\r invalid option`、路径尾部带 `\r`、`do\r` 语法错误、MySQL 双引号过滤返回空但全表查询存在目标行。
- Verification: 记录 SSH 命令不含 `-n`，远端脚本以 UTF-8 bytes 发送，`.env IMAGE_TAG`、镜像、health、release-info、release lock 与 migration failed count 均结构化断言通过。
- Forbidden action: 不得把 stdin 未发送、CRLF 污染或 SQL 引号误判造成的空输出当作服务器运行态失败；不得因此跳过 release lock 或 migration 核验。
- Evidence: `doc/tasks/20260713-current-head-test-only-release/execution-log.md` 的 `ssh-stdin-n-flag`、`windows-textmode-crlf`、`mysql-double-quote-filter`。
- 2026-07-31 追加证据：远端验收必须用 LF 二进制 stdin 后再采信 `.env IMAGE_TAG=release-20260731-smartseed-tempfix-head-test-r260731d-r1`、backend/frontend image tag、release lock `APPLIED`、migration failed/running count `0`；首次 CRLF 输出不得写入最终验证报告。

## 2026-07-13 Python f-string literal braces 与远端验收脚本门禁

- Trigger: Windows 本机用 Python 组装包含 bash、SQL、JSON、Docker format 或 JavaScript 对象字面量的远端验收脚本。
- Preflight check: 不用 f-string 包裹含大量 `{}` 的脚本文本；优先使用 ASCII 占位符加 `.replace(...)`、`string.Template` 或外部 UTF-8 脚本文件；发送 SSH 前先本地执行最小语法检查，确认无 `SyntaxError` 且尚未连接远端。
- Blocker: 本地出现 `SyntaxError: f-string: valid expression required before '}'`、格式化占位符与脚本文本冲突、无法证明失败发生在本地且远端未执行。
- Verification: 记录首次失败为本地 carrier 错误、无服务器动作发生；改写后 SSH 退出码为 0，并结构化验证 `.env IMAGE_TAG`、镜像、health、release-info、release lock 和 migration 状态。
- Forbidden action: 不得为了绕过 f-string 错误改远端脚本逻辑、跳过 release lock/migration 核验，或把本地 carrier 失败当成测试服发布失败。
- Evidence: `doc/tasks/20260713-current-head-test-only-release-rerun/task.md` P005，releaseTag `release-20260713-current-head-test-r260713u`。

## 2026-08-01 PowerShell 远端验收与 closeout 自匹配门禁

- Trigger: PowerShell 中通过 SSH 查询远端 MySQL、验证 `/actuator/health`、恢复 48181 运行控制台、扫描进程或清理 release worktree。
- Preflight check: `ssh -> docker exec -> mysql` 多层命令优先用 Python/PowerShell 参数数组或 UTF-8 LF stdin，不把四层引号压进一个 PowerShell 字符串；`Invoke-WebRequest.Content` 必须识别 byte[] 并按 UTF-8 解码；进程扫描必须限定进程名并排除当前检查器；本机策略拒绝宽脚本时拆成可审计小步骤。
- Blocker: 本地 shell 报引号未闭合、health 200 但 body 断言因 byte[] 失败、进程扫描命中当前校验脚本、或批量脚本被策略拒绝且没有拆分执行证据。
- Verification: 记录 carrier exit code、decoded health body、被采信的 java.exe PID/CommandLine、stdout 必需字段完整性、cleanup path allowlist 和最终 `passed=true` 证据。
- Forbidden action: 不得把本地 carrier/编码/自匹配失败当作测试服业务失败；不得因此跳过 release lock、migration、运行控制台主路径或 worktree 物理目录复核。
- Evidence: `doc/tasks/20260801-head-test-only-release/execution-log.md` I012-I016；`remote-runtime-verification-r260801e-r1.json`、`runtime-control-main-restore-r260801e-r1.json`、`worktree-cleanup-r260801e-r1.json`。