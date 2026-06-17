# 任务: 新增本机前后端重启 bat

## 任务目标

创建一个可双击执行的 bat 文件，用于重启本机 IntRuoyi 前端与后端。

本任务只新增本机入口脚本，不执行真实重启、不操作远端服务器、不写入数据库或对象存储。

## 经验门禁

- `docs/experience-index.md`：本任务命中“重启”相关门禁，需要明确本次仅创建本机入口，不执行长链路或高风险动作。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：正式服默认禁止操作；测试服、备份服、正式服写入或重启必须有用户当前任务授权。本任务不调用远端重启脚本、不写入凭据、不执行 SSH。
- 本机 IntRuoyi 固定路径：后端 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`，前端 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。bat 只检查必需脚本是否存在，缺失即失败。
- `是否从根因和长期维护角度解决`：是。双击入口复用原 IntRuoyi 已维护的本机重启脚本，不复制重启逻辑。
- `是否存在临时补丁或绕过`：否。

## 里程碑

- [x] 创建任务目录与任务文档。
- [x] 写入 BDD 场景和 RED 验证。
- [x] 新增可双击 bat 文件。
- [x] 运行静态与 cancel 分支验证，避免验证阶段触发真实重启。
- [x] 更新执行日志、请求命令记录和最终状态。

## 预期验证

- RED：目标 bat 不存在时验证失败。
- GREEN：目标 bat 存在，内容调用原 IntRuoyi 本机重启脚本并传入 `-Component full`。
- GREEN：`cancel` 分支可通过 `cmd /d /c` 执行且不会触发真实重启。

## 当前状态

已完成。

## 最终验证

- `RED: PowerShell 检查 restart-frontend-backend.bat -> FAIL, Missing expected restart bat`。
- `GREEN: cmd /d /c restart-frontend-backend.bat cancel -> PASS`。
- `GREEN: PowerShell 静态检查 bat 路径、-Component full 与 cancel 分支 -> PASS`。
- `GREEN: git diff --check -> PASS`，仅提示 `docs/request-command-log.md` 下次由 Git 触碰时会将 LF 转为 CRLF。
- `GREEN: task-closeout-cleanup --mode preview -> PASS`，无删除项、无阻塞、无警告。

## 交付文件

- `restart-frontend-backend.bat`
