# 执行日志: 新增本机前后端重启 bat

- `BDD: 双击重启本机前后端 -> Given 操作者在维护仓库中双击 bat 文件, When bat 校验原 IntRuoyi 本机重启 PowerShell 脚本存在, Then 它应调用该脚本并以 Component=full 重启本机前端与后端；如果必需脚本缺失则立即失败。`
- `GREEN: experience-preflight -> PASS，本任务只创建本机 bat 入口并验证 cancel/静态契约，不执行真实重启、不操作远端服务器、不写入数据库或对象存储。`
- 只读检查：当前维护仓库复制的 `ops\deploy\restart-int-ruoyi-local.ps1` 默认解析到 `D:\ProjectPackage\Int\yudao-ui-admin-vue3` 并失败；因此 bat 必须显式调用原 IntRuoyi 后端仓库中的 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\deploy\restart-int-ruoyi-local.ps1`。
- 只读检查：原 IntRuoyi `worktree-port-map.ps1` 可解析 `int_main` 到前端 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`、后端 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`、端口 `8081/48081`。
- `RED: PowerShell 检查 restart-frontend-backend.bat -> FAIL, Missing expected restart bat: D:\ProjectPackage\Int\IntRuoyiMaintance\restart-frontend-backend.bat`。
- 新增 `restart-frontend-backend.bat`，双击默认调用 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\deploy\restart-int-ruoyi-local.ps1 -Component full`，缺少脚本时 fail fast；保留 `cancel` 分支用于安全验证。
- `GREEN: cmd /d /c restart-frontend-backend.bat cancel -> PASS`，输出 `[INFO] Restart cancelled.`，未触发真实重启。
- `GREEN: PowerShell 静态检查 bat 路径、-Component full 与 cancel 分支 -> PASS`。
- `GREEN: git diff --check -> PASS`，仅提示 `docs/request-command-log.md` 下次由 Git 触碰时会将 LF 转为 CRLF。
- `GREEN: task-closeout-cleanup --mode preview -> PASS`，无删除项、无阻塞、无警告。
