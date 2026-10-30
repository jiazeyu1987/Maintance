# Spug 资源包接管安装与只读验收

## Current Status
completed

安装接管验收通过并保留发现项（PASS_WITH_FINDINGS）。源电脑修复58回程后，本机2026-10-30 23:07直连22/8081/48081全部成功；SSH确认回程经172.30.30.1/ens18。三服前后端实际镜像ID及RepoTags精确匹配原manifest，页面版本均为2026-10-30-10-19-11、HTTP200、backend health=UP。真实Chrome登录和232条历史/25个包复验通过。没有跳板、远端修复、发布或业务写入。

既有发现项继续记录：57旧Compose目录.env的IMAGE_TAG为current-32ff79d-20261020；58/59当前容器无Compose标签，不能据此推定.env路径。实际执行器以Docker API按镜像ID替换容器并保留旧Config/Labels（intruoyi_runtime_agent.py:617/665），所以版本验收采用实际.Image/RepoTags与原manifest交叉证明。本任务没有执行发布，不宣称发布operation=SUCCESS或完整发布门禁通过，也未修改这些既有文件。源电脑路由修复的重启持久性未通过服务器重启验证。

## 任务目标
保留原始资源包及已有本地修改。先校验 C:\Users\D01021\Documents\spug-handoff-minimal-20261030，再获取用户指定维护仓及 IntRuoyi 分支与必含提交；独立副本仅同步代码，保留凭据、历史、版本绑定和镜像。重新生成独立副本清单后安装，启动前等待用户确认原电脑执行器已停止，并确认导出后无新发布。普通脚本运行，真实 Playwright 登录，只读核验发布历史和三服版本，不发布、不修改业务数据、不安装服务。

## 里程碑
- [x] M1 原包结构与原始 integrity 校验通过；用户确认导出后无新发布。
- [x] M2 两个指定分支的 HEAD 即必含提交；独立副本代码同步完成。
- [x] M3 路径、依赖与新校验清单完成；用户两项启动前提已确认，完整Git源码已用于安装。
- [x] M4a 普通脚本安装运行、真实登录、发布历史和本机运行态验收。
- [x] M4b 三服只读运行版本验收：57/58/59实际镜像、标签、页面版本、健康与HTTP均通过；既有Compose文件发现项如实记录。
- [x] M5 已交付验收记录、访问地址、启动命令；稳定路径与私密会话清理复核完成，仅提交本任务脱敏记录。

## 预期验证
原始所有清单项逐字节 SHA256/长度及路径安全校验；Git 分支祖先关系；仅代码差异及私密状态完整性；独立副本新清单；本机依赖与路径；真实登录及历史、版本与三服运行证据对应。失败保留原证据，缺条件立即阻塞，不以 mock 或猜测替代。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；使用指定配套代码与正式安装入口，先核脚本契约。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- 本轮网络诊断：Trigger=同网段目标连通性不一致；Preflight check=核实原包实际密钥及known-hosts路径、-F NUL/BatchMode/StrictHostKeyChecking/IdentitiesOnly、逐目标选源地址/网关/接口/路由；Blocker=认证前TCP超时、无法从58读取防火墙证据；Verification=三目标路由和三端口并行探测、SSH分阶段退出证据；Forbidden action=打印密钥、改凭据/应用/网关、通过57/59代理连接58、未经证据认定来源IP被封；Evidence=本轮网络JSON与execution-log.md。
- Trigger：Windows 接管安装、完整性检查、Git 同步、真实 E2E 与三服只读验证。
- Preflight check：显式 UTF-8；按 experience-index 路由读取命中文档；原包只读；指定提交已提交内容；核对安装脚本契约；启动前确认原执行器停止及导出后无新发布。
- Blocker：原清单失败、必含提交缺失、私密状态不完整或过期、原执行器未确认停止、真实登录/运行依赖缺失均停止相应阶段。
- Verification：保留原包校验与差异证据；真实 Playwright 页面登录；历史及远端版本只读比对，任何未验项不计通过。
- Forbidden action：运行包内旧安装脚本、覆盖原包或本地改动、Git 模板覆盖凭据/历史/绑定/镜像、输出或提交凭据、安装服务、发布或业务写入、猜测最新状态。
- Evidence：execution-log.md 与本任务脱敏证据文件；真实 E2E 前记录 experience-preflight PASS。

## 上一任务检查
本线程未识别到既有自有任务链。bootstrap 读取的其他历史任务属于并发/历史工作，不接管、不修改。

## 待确认
用户已逐项明确确认：导出后没有再发布；原电脑执行器已停止。此启动前提已满足。

## 校验进展
原清单 656 个文件、2,318,944,629 字节逐项 SHA256 全部匹配；SQLite immutable 只读 integrity_check=ok，25 个包、232 个历史作业、无 running/queued。原包额外有两个未列入清单的说明文件（使用说明.md 和乱码文件名说明），单独记录，不能将它们称作已验证清单项。原包未修改。
任务开始时维护仓int_main HEAD=d8bdbcd40260d6f8f9536c14e150ab15cec8aa82，已有1528个改动/未跟踪条目；不切分支、不覆盖，安装使用独立Git克隆。最终仅按自动提交规则选择本任务脱敏记录，排除所有既有源码/配置改动。
规则引用的 E:\IntRuoyi 文档与 D:\ProjectPackage\AGENTS.md 均不存在；已从指定提交读取对应正式文档。Playwright采用资源包随附版本及已安装Chrome，未假造缺失路径。初检python命中WindowsApps别名；现已部署独立Python并由运行包装脚本显式加载。

Git 副本位于 C:\Users\D01021\Documents\spug-handoff-work-20261030\code\{Maintance,IntRuoyiAll}。已从指定 IntRuoyi 提交取得 docs/powershell-memory.md、docs/server-access.md、docs/release-backup-restore.md、docs/login-access.md；按用户明确要求适配本电脑路径。文档引用的原机盘符不伪造，凭据仅从资源包读取。
435 个代码项与指定维护仓提交比较：57 字节相同、378 仅 CRLF/LF 不同、零语义差异；独立 package 副本按 Git blob 同步，219 个非代码受保护清单项原字节相同。原清单证据独立保留，新清单 659 项全部通过。

## 本机安装方案与依赖
安装目标调整为 C:\SpugHandoff\release，新建父目录及工作副本 ACL 只允许当前用户、SYSTEM、Administrators；原包 ACL 不动。普通脚本位于 C:\Users\D01021\Documents\spug-handoff-work-20261030\{runtime-env,install-local,start-local}.ps1。
已验证独立 Python3.12.14（复制已安装 bundled runtime 的标准库/DLL，不含其 site-packages）、JDK21.0.13（官方 ZIP SHA256 和 Microsoft Authenticode Valid）、pnpm9.15.9、Node24.19、Maven3.9.12 UTF-8、Docker29.9.1 和 Chrome。系统全局 PATH 不变。Python 官网安装器网络超时且文件为0；未执行该安装器，已停止本任务下载过程，不把它算安装成功。

## 网络阻塞解除
此前58的192.168.96.0/20 Docker网桥覆盖本机192.168.109.82，源电脑提供了错误回程证据并随后自行修复。本机23:07重测三端口均通，SSH实际读取回程192.168.109.82 via172.30.30.1 devens18，直接会话来源仍为192.168.109.82。没有使用57/59跳板；此前抓包结果不再是完成运行验收的前提。网络历史及失败证据保留在execution-log.md和network-diagnosis.md。

## 本机最终验收
- 安装器退出0；659清单项与25包验证通过。原包最终复验656项PASS，原清单SHA不变；工作包659项PASS、无额外文件。
- 真实Chrome/Playwright从Spug登录页输入私密文件中的原账号，收到HTTP200且error=false；按原页面确认来源IP提示后进入发布中心。未修改账号、凭据或认证逻辑。
- 页面任务表232行的任务ID、操作、原状态和固定版本逐行匹配；25个包版本及阶段选项匹配；三服登记快照均保留原版本。发布中心非GET请求=0，唯一POST为真实登录。
- 启动后SQLite使用mode=ro读取含WAL的真实状态，与已审阅的路径/省略标记转换完全相同；25包、232作业、0活动任务。三个旧Spug worker/monitor/scheduler的autostart=false。
- 新Docker项目intruoyi-spug-handoff-20261030：db healthy、spug running；执行器普通Python进程监听18112，无Windows服务。旧18080项目未动。
- 访问：http://127.0.0.1:18081/release-center/?app=intruoyi 。安装根C:\SpugHandoff\release；运行入口C:\Users\D01021\Documents\spug-handoff-work-20261030\start-local.ps1。
- 日常启动与路径说明：C:\Users\D01021\Documents\spug-handoff-work-20261030\START-HERE.md。当前实例已运行，不重复启动执行器。

## 收口与保留
未进行发布/构建，因此未创建临时发布worktree，无合并或删除项；两个独立代码克隆属于安装输入，保留。维护仓原现场未checkout/reset/clean，未暂存或提交任何私密资料。58阻塞已通过直连与实际运行证据解除。本任务没有仓库生产实现改动；只提交独立脱敏任务记录，不提交安装private、浏览器会话、原包、镜像、历史数据库或既有源码/配置。
普通脚本控制台已落在稳定安装路径，新实例按用户要求保留运行；未停止其他并发实例。私密浏览器会话文件验收后删除，截图和私密历史辅助输入仅在安装private目录，脱敏JSON证据位于本任务目录。
最终证据acceptance-final.json，状态PASS_WITH_FINDINGS；本任务范围内没有剩余阻塞。既有发现项保留，没有扩大为本次远端修复或后续发布授权。
