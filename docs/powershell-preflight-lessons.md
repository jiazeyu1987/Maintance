# PowerShell 事前经验清单

## 适用范围

当任务涉及 Windows PowerShell 5.1 命令执行、脚本排查、中文文件读取、中文日志输出或多条命令串联时，先读本文。

本文只沉淀可复用的 PowerShell 事前门禁；具体业务发布、备份、恢复和 E2E 规则仍以对应业务文档为准。

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
