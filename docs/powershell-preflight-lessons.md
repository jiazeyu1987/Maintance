# PowerShell 事前经验清单

## 门禁摘要

- Trigger: Windows PowerShell 5.1、中文文本、here-string、管道、SSH、MySQL、外部命令退出码或运行控制台脚本任务。
- Preflight check: 先读取权威共同规则 `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`，再读取本文的维护仓专项增量；设置 UTF-8 编码并设计后置断言。
- Blocker: 共同规则未读取、中文编码链路不明确、命令依赖 `&&`、只看 stderr 或进程退出而没有结果断言。
- Verification: UTF-8 回读、`$LASTEXITCODE`、结构化响应、目标文件/数据库/远端状态后置校验。
- Forbidden action: 不得把本文当作另一套共同 PowerShell 标准，不得用管道乱码、静默 warning 或默认编码继续长链路操作。
- Evidence: 命令、stdout/stderr、字节或文本回读、任务 execution-log 和目标状态断言。

## 适用范围

当任务涉及 Windows PowerShell 5.1 命令执行、脚本排查、中文文件读取、中文日志输出或多条命令串联时，先读本文。

PowerShell 共同基础规则以 `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md` 为唯一权威来源；本文只沉淀维护仓、运行控制台和构建发布专项增量。若文字重复，以共同规则为准；维护仓更严格的专项门禁继续叠加执行。具体业务发布、备份、恢复和 E2E 规则仍以对应业务文档为准。

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

- Python `subprocess.run(..., text=True, input=script)` 在 Windows 上可能把 `\n` 转为 `\r\n`，远端 `bash -s` 会报 `set: -\r invalid option`、路径尾部出现 `\r` 或 `do\r` 语法错误。
- 推荐写法：`input=script.encode('utf-8')`，按 bytes 发送；stdout/stderr 再显式 `decode('utf-8', errors='replace')`。
- 执行前可检查脚本字节不含 `\r`；失败时保留 stderr，禁止把远端脚本未执行误判为服务器或数据库异常。

## 2026-07-10 原生命令 stderr 与 PowerShell 自动变量门禁

- `git checkout` 等原生命令可能在成功且退出码为 0 时向 stderr 输出正常提示；`$ErrorActionPreference='Stop'` 不能代替 `$LASTEXITCODE` 判断。
- 需要可靠捕获时使用 `Start-Process -Wait -PassThru` 配合 stdout/stderr 文件，并以 `ExitCode` 为准；正常 stderr 作为证据记录，不直接判失败。
- PowerShell 变量后紧跟冒号时使用 `${Path}:`，避免 `$Path:` 解析错误。
- 不把函数参数命名为 `$Args`；它是 PowerShell 自动变量，容易造成数组绑定和参数读取异常。

## 2026-07-10 HTTP 健康检查与进程路径扫描门禁

- `Invoke-WebRequest.Content` 在不同 PowerShell/HTTP 响应组合下可能是 `byte[]`，不得直接使用 `-match 'UP'`；JSON 健康接口优先用 `Invoke-RestMethod` 并断言结构化 `status`。
- 若必须使用 `Invoke-WebRequest`，先按响应编码将字节显式解码，再做字符串或 JSON 判断。
- 按命令行扫描占用某个 worktree 的进程时，清理命令自身也会包含目标路径；必须排除当前 `$PID`，再检查剩余进程，避免把执行壳误判为外部锁定进程。
