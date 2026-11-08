# 目录身份修复部署计划

## Current Status
ready_for_closeout — 候选实现已由根任务提交 `b5c8817de2b4cc5efdad566f0fb65fdabefcb8d8`，本子项 Windows 66 / Linux 15 回归通过，专属干净构建与安装 prepare-only 已完成，尚未执行 apply。根任务协调当前 FULL373 后才允许精确控制组件重载。实际预检原件为 `catalogue-identity-install-plan-b5c8817.json`，runtimeWrites=0。

## 源码和部署闭包
- 唯一安装输入：根任务新建的专属 `PRIVATE/release-b5c8817` 干净 worktree，HEAD 必须为上述完整提交；不能从当前脏工作区或迁移快照获取新代码。
- Windows 18112：仅安装新提交 `executor.py` 和与已部署原件同源的 `package_catalog.py`、`package_presence.py`；其它实际发布源码保持。实际 executor 和候选差异仅新增 `/identity`、保留当前仓库 current/database-version 路由；实际已运行的 `git log --all --date-order` 已正式纳入，不能回退。
- 18080 的 bridge：仅安装 `application_registry.py`、`release_http.py`；原 `spug_bridge.py` 认证/权限边界、nginx、配置文件与 smallapp entry 不改。
- 后台清单投影不在本次修复。`/state` 及81MB旧历史保留；不删除已停用来源或旧包，不改变NAS根。

## 已核实际进程管理
- 18112 原进程为 PID35788，创建时间 `1793775245.2357974`；普通 Python 进程，无 SCM 归属，唯一子进程是其 conhost。原 exe/argv/cwd/env 原件及摘要仅存在 PRIVATE，不凭端口重建命令。原 exe 为 handoff Python3.12.14；config pin SHA `e03e70f9e386efa4f4a35f38cb3747f577e37152169e38a4d5562149e6ee623e`。
- 18080 精确容器为 `f615a60c76f46e4f6ae20ea6298f737fb9786684ce941fcc15763654461265bf`；bridge PID2124 是 PID1 supervisord 的 `program:release-center-bridge`，`autorestart=unexpected`、`exitcodes=0`。实际配置没有 supervisorctl section，直接调用已失败并保留原件；不能误称已通过 supervisorctl。安装只对核对 `/proc` argv/startTime/PPid 的原 child 发送 SIGTERM，由既有 supervisor 按原策略重启；不重启 supervisor 或容器。
- bridge 私密配置 pin SHA `2e7ead665bfdeafb439c5b5b1bbead070451e759db3f2bfb6a4732c7f9116f41`；supervisor/nginx/locations pins 随 prepare 固定。被保护进程当前 smallapp entry PID124978、正式来源控制 PID25086，安装前后必须一致。
- 发布历史309 jobs，无 running、无重载构造函数会改写的特殊 interrupted job；纯 SQL payload SHA `bd65b05d8c1cd26f8c3c33de7b45708f5cf074cd4006c9ad4b915cd1d2c42284`。每次 apply 前重新读取，漂移则停止，不拿旧快照放行。

## Helper与阶段门禁
`install_catalogue_identity.py --commit <完整commit> --worktree <本任务干净worktree>` 默认只 prepare：核 Git 已提交文件、进程创建时间/argv/exe/cwd、容器映射和准确挂载、完整原文件/config pins、原309 jobs、无部署子进程、独立来源控制 PID。使用 SQLite backup API备份原库，原文件/配置只保存 PRIVATE；不运行 service 构造，不改安装位置。

只有根任务协调后传入 `--apply` 才执行：再次验证全部准备原件 → 精确终止原空闲 Windows executor → 确认原 payload/jobs 未变 → 从干净提交写完整候选文件 → 原 exe/argv/cwd/env 无窗口启动 → 认证 `/identity` 200且正确身份 → 更新 bridge两文件 → 精确 bridge child重载 → 实际新 registry GET清单200 → 前后 history/config/保护PID、无关18081实例状态完全一致。

任何失败写 `CatalogueIdentityInstallation/v1 status=FAIL`，保存阶段、原备份和私密错误；不回退 `/state`、不盲重试业务、不覆盖失败报告。若 executor已经停下但新进程失败，根任务先诊断新日志，只有明确恢复原组件时才从精确原备份恢复原文件/原命令；SQLite始终不被替换。

主报告固定 `catalogue-identity-installation.json`，字段schema已与UI agent协调：status/sourceCommit/buildWorktree、executor/bridge runtime实际PID及filePins/configPin、history前后payload/jobs摘要、PRIVATE backup pin、四项保护布尔证明。CLI清单200仅控制验收，`realBrowserVerified=false`；实际Spug页面验证另存证据，原两份504始终保留。

## BDD / TDD与经验门禁
- RED：原真实 Executor `/identity` 409、registry只访问/state，3条新行为失败。
- GREEN：轻量身份认证/锁独立、清单只请求identity+catalog、错应用拒绝、旧历史保持。
- RED→GREEN：真实 socket 慢响应头 0.2s期限实测0.782s失败，精确socket截止shutdown后通过；持续少量正文同样有界。
- RED→GREEN：原真实 Git 测试无法选择独立分支提交，恢复已部署 `--all --date-order` 一行后通过。
- REGRESSION：Windows `catalogue-identity-regression.json` 66条、Linux `catalogue-identity-linux.json` 15条均通过；固定SHA、零skip、network none、只读输入、独立测试容器已删除。旧版本测试首次缺psutil属于环境失败，任务私有固定psutil7.0.0补齐后通过。
- Trigger/Preflight/Blocker/Verification/Forbidden/Evidence正式归宿为 `docs/release-agent-checklist.md#包清单身份与桥接期限门禁`。未记录根任务 `GREEN: experience-preflight -> PASS` 不得apply。

## 实际差异边界
身份仅严格核已认证 app id、固定 origin并禁止redirect；展示repo与实际repo不同是既有事实，不改配置伪造一致。正文预算身份4KiB/元数据16MiB/状态128MiB，普通20秒/既有数据库检查60秒；连接后socket绝对期限已测，DNS仍由操作系统resolver负责，不将未覆盖阶段宣称为可强杀。新模块不会把失联或未知HTTP错误当空清单成功。
