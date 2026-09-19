# Execution Log

## BDD Scenarios

BDD: 固化提交并隔离构建 -> Given 源工作区可能存在未提交改动且系统持续更新 / When 在发布开始时记录当前分支与 HEAD 并从该提交创建本次专用临时 worktree / Then 临时 worktree 干净、HEAD 固定且所有构建输入只来自该已提交快照。

BDD: 仅测试服发布 -> Given 发布包、manifest、版本号和变更说明均与固化提交一致 / When 执行同一 releaseTag 的 build-release 与 publish-test / Then 测试服运行态全部通过且未执行 mark-tested、promote-prod 或 promote-backup。

BDD: 运行控制台可追溯 -> Given 测试服已运行本次镜像 / When 通过真实前端路径检查页面与运行控制台 / Then 页面可访问且控制台显示本次版本号与变更说明。

## Preflight

- 2026-08-16：收到仅测试服发布目标；要求以发布启动时当前分支 HEAD 为唯一快照，后续不跟随开发分支更新。
- 已执行唯一只读 UTF-8 bootstrap，读取适用 AGENTS、最新任务状态、`docs/experience-index.md` 与 `E:\IntRuoyi\docs\powershell-memory.md`。
- 最新目录任务 `20260813-r260812b-experience-consolidation` 为 `in_progress`，当前无证据属于本线程任务链；不修改、不阻塞，除非后续发现共享资源冲突。
- 已按经验索引读取测试服发布、构建、PowerShell、服务器访问、登录、worktree 和收尾正式文档；正式 worktree 根使用 `D:\IntRuoyiWorktree\`。
- GREEN: experience-preflight -> PASS；目标环境仅 test=`172.30.30.58`，releaseTag=`release-20260816-intmain-head-test-r260816a-r1`，禁止 mark-tested/promote-prod/promote-backup/正式服/备份服动作。允许进入本任务 worktree 创建、构建、测试服发布和真实页面验收。

## Commands And Results

- 只读引导：读取适用规则、经验索引、PowerShell 经验与最近任务状态；结果 PASS，命令输出发生工具显示截断，后续将按索引定向读取命中文档，不依赖截断片段作发布决定。
- 经验定向读取：测试服发布主入口、构建经验、发布 checklist、PowerShell 专项、服务器/登录/发布正式规则、worktree 限制与删除门禁、编码和 closeout 规则均读取完成；结果 PASS。
- Git 冻结：维护仓 `int_main@3cd1f3e7e99fa397497107708a9ba977d5879749`，主程序仓 `int_main@cb0464ce886973f16136ed31b4d5812d28927eb3`；两个主工作区均很脏，禁止直接构建，必须从上述固定提交创建 clean worktree。
- Git 仓库关系：`E:\IntRuoyi\IntRuoyiBackend` 与 `E:\IntRuoyi\IntRuoyiFronted` 均解析到同一 Git 顶层 `E:\IntRuoyi`，本轮主程序只创建一个 worktree，避免重复/冲突注册。
- Worktree 创建：维护仓执行 `git worktree add --detach D:\IntRuoyiWorktree\r260816a\m 3cd1f3e...`，主程序执行 `git worktree add --detach D:\IntRuoyiWorktree\r260816a\a cb0464ce...`；两条命令退出码均为 0。
- Worktree 验证：维护 worktree HEAD=`3cd1f3e7e99fa397497107708a9ba977d5879749`、主程序 worktree HEAD=`cb0464ce886973f16136ed31b4d5812d28927eb3`，两者 detached 且 `git status --porcelain --untracked-files=all` 均为 0 项；Git 注册和物理路径均存在。
- 发布契约：维护仓修复提交 `97723ac524487595ab5b145e31251d6bc1ec0091` 是冻结维护 HEAD 的祖先；运行控制台 action 显式指向维护 worktree 的 `ops/deploy/publish-int-ruoyi.ps1`，该脚本调用维护 `ops/release/run-release-migration-policy-gate.py`。
- GREEN: release-migration-policy -> PASS；维护权威 gate 扫描冻结主程序 SQL，`status=passed`、`migrationCount=490`；迁移/required SQL 合同 pytest `16 passed`，发布 PowerShell parser errors=`0`。
- 本机前置：Java 21.0.10、Maven 3.9.9、Node 24.12.0、Corepack pnpm 10.25.0、Python 3.12.10、Docker 29.2.1/BuildKit 0.27.1 可用；可用物理内存约 12510 MB、虚拟内存约 23813 MB；48181/48182 均无监听。
- Docker 基线：本机配置的 primary mode=`offline-tar`；后端基础镜像 tar 存在且 SHA256 与配置一致，加载后 image id 与配置 digest 一致；前端 `nginx:1.27-alpine` 本地镜像存在并记录 image id。
- 依赖恢复：维护控制台前端和主程序前端均使用 `corepack pnpm@10.25.0 ... install --frozen-lockfile`；主程序前端 1103 个包全部从本地缓存复用，下载数为 0。两个工作树均将 pnpm 报告的精确 ignored-builds 清零，临时允许列表随后恢复到冻结提交，最终 `git status --porcelain --untracked-files=all` 为空。
- GREEN: maintenance-console-build -> PASS；`scripts/build.ps1` 完成前端 typecheck、Vite production build、后端 26 项测试与 Spring Boot jar 打包，`BUILD SUCCESS`，jar 大小 35141821 字节，SHA256=`4e84e0c1039251406f679e9a3e210fc765d4424d86f68d11fa3974f897740198`。
- 运行控制台：从既有本机配置生成本任务 gitignored UTF-8 local config，只改为冻结前后端/维护 ops/state 路径，并显式设 test enabled、prod/backup disabled；PID 27460 从 release worktree jar 启动，48181 health=`UP`。
- Build preview：action=`build-release`、environment=`release`、publishScope=`code-only`、releaseTag=`release-20260816-intmain-head-test-r260816a-r1`，脚本及前后端根均来自冻结 worktree，forbidden mode count=0，releaseTag collision count=0。
- GREEN: build-release -> PASS；仅提交 operationId=`op-2026-08-15T174726309062300Z-9a359a99-a27b-4b1b-97a9-0d45c3bffd89`，最终 `SUCCESS`。主程序 Maven 30/30 模块成功（25:18），前端 `build:test` 成功，后端/前端镜像构建成功，镜像 tar 734803456 字节，发布包上传 NAS 成功。
- GREEN: manifest-and-source-verification -> PASS；维护 validator=`MANIFEST_VALIDATION_PASSED`，Manifest v1 releaseTag/publishScope/sourceRepos、legacy manifest gitCommit、前端 release-info、changeSet、镜像 artifact size、两 worktree HEAD/clean 共 22 项断言全部通过。Manifest v1 两个 sourceRepos 均为 `cb0464ce886973f16136ed31b4d5812d28927eb3`、dirty=false；changeSet 与同一 releaseTag、组件 `intruoyi` 绑定。
- 测试服写入前只读状态：SSH 仅访问 `172.30.30.58`；无 RUNNING release lock，最近正式 lock 为 r260812b-r2=`APPLIED`。现有 `.env`/backend/compose 指向 `hotfix-20260814-route-submit-order-r1`，但 frontend 实际容器与 `/release-info.json` 仍为 r260812b-r2；3 条 FAILED migration 均为 2026-06/07 历史 releaseTag，不属于本轮目标。
- GREEN: publish-test-preview -> PASS；从已保存 preview 结构化验证 action=`publish-test`、mode=`deploy-release`、environment=`test`、ServerHost=`172.30.30.58`、RemoteAppDir=`/opt/intruoyi/runtime`、目标 releaseTag 与冻结值一致、forbidden action count=0；尚未提交服务器写操作。

## Problems

### P-001 工具输出截断

- 现象：首次只读引导输出约 25k token，工具界面截断中部内容。
- 阶段：M1 经验预检。
- 影响：不能仅凭该输出确认经验索引全部命中项和 PowerShell 文档全部内容。
- 原因判断：一次读取多个较长文档超过显示预算。
- 处理动作：任务文档建立后按索引和本次发布关键词定向读取，逐份保留完整输出。
- 结果：已通过定向分段读取解决；后续不再一次输出多个长文档。
- 是否可前置检查：是，先统计文件大小和标题后分段读取。
- 是否可自动化：是，发布预检脚本可输出命中清单与摘要并为完整文档保留哈希。
- 下次如何避免：只读 bootstrap 先输出路由与文件清单，任务文档建立后逐份读取命中文档。

### P-002 worktree 路径文档口径不一致

- 现象：维护仓 `test-release-preflight.md` 仍推荐历史根 `D:\ProjectPackage\Int\IntRuoyiWorktrees\...`，而 2026-08-15 更新的正式 `E:\IntRuoyi\docs\worktree-restrictions.md` 强制所有 IntRuoyi worktree 位于 `D:\IntRuoyiWorktree\`。
- 阶段：M1 发布隔离预检。
- 影响：照旧推荐路径创建会违反当前强制限制，并可能绕过端口/登记表治理。
- 原因判断：维护仓经验入口尚未同步新的正式 worktree 根规则。
- 处理动作：本轮采用正式强制根 `D:\IntRuoyiWorktree\r260816a`，不使用旧推荐路径；成功后更新既有经验入口和索引/checklist。
- 结果：已按正式根创建并验证两个 clean detached worktree，旧推荐路径未使用。
- 是否可前置检查：是，创建前解析并断言目标绝对路径属于 `D:\IntRuoyiWorktree\`。
- 是否可自动化：是，发布预检可直接调用路径守卫。
- 下次如何避免：同步 `test-release-preflight.md` 的推荐命令和路径示例到正式根。

### P-003 主工作区极脏且 Git 状态含失效目录警告

- 现象：维护仓 dirty 49 项；主程序 dirty 252 项。主程序状态扫描还对历史 `target_corrupt_m4_20260802_1327` 输出多个目录不可读 warning。
- 阶段：M1 Git 状态检查。
- 影响：主工作区不具备可证明的发布输入；直接构建会混入未提交内容，失效目录 warning 也会放大状态输出并降低审计可读性。
- 原因判断：大量并发开发/任务文档/运行产物并存，且历史损坏 target 残留仍在主工作区。
- 处理动作：不修改、不提交、不清理任何非本任务内容；从冻结 HEAD 创建本轮专用 clean worktree，后续构建来源仅认 worktree 与 manifest。
- 结果：冻结提交已记录，两个 release worktree 的 HEAD 均与冻结值一致、detached 且 clean；主工作区脏内容未进入发布输入。
- 是否可前置检查：是，按仓库输出 dirty 计数、staged/unstaged/untracked 分类和 stderr warning 摘要。
- 是否可自动化：是，生成 frozen-baseline JSON 并在构建后自动比较 manifest。
- 下次如何避免：保持发布输入始终从 clean detached worktree 创建；另开独立任务治理历史损坏 target，不在发布任务中顺手清理。

### P-004 主程序旧迁移检查器与权威发布检查器不一致

- 现象：冻结主程序 `IntRuoyiBackend/script/release/run-release-migration-policy-gate.py` 对 C00 `type=backfill` 返回 `invalid type`；维护仓权威 gate 支持 `preflight/backfill/postflight/rollback-dry-run` 并排除 evidence-only SQL。
- 阶段：M3 构建前迁移契约。
- 影响：若误用主程序旧检查器会产生假阻塞；若发布链实际误指向该副本则会在构建阶段失败。
- 原因判断：同一仓群保留了主程序旧副本，而维护控制台正式 action 已切到维护 `ops` 源；文档示例仍存在旧入口。
- 处理动作：停止构建后核对 RuntimeControl action、publish 脚本调用链和修复提交祖先关系；运行维护权威 gate、16 项合同测试和 PowerShell parser。
- 结果：权威发布链 PASS，490 个迁移可解析，evidence-only 不进入 required SQL；本轮不调用主程序旧副本，不把其失败当作发布成功证据。
- 是否可前置检查：是，预检应同时输出 action script path 和 policy gate path。
- 是否可自动化：是，增加“同名旧副本不得被 RuntimeControl 引用”的静态合同，并在文档只保留权威入口。
- 下次如何避免：在既有发布经验中明确维护 `ops` 为 RuntimeControl source of truth，并治理或同步主程序副本。

### P-005 `rg` glob 参数位置导致诊断噪声

- 现象：一次 `rg` 调用把 `-g '*.py' -g '*.ps1'` 放在路径之后，PowerShell/rg 将其部分解释为文件路径并输出 `系统找不到指定的文件`。
- 阶段：M3 测试定位。
- 影响：只影响诊断输出，后续命令仍找到目标测试；未修改文件、构建产物或远端。
- 原因判断：命令参数顺序不符合当前 Windows rg 解析路径。
- 处理动作：后续 glob 选项放在搜索路径之前，目标测试改用明确文件路径执行。
- 结果：16 项目标 pytest PASS。
- 是否可前置检查：是。
- 是否可自动化：部分，可封装固定搜索命令。
- 下次如何避免：Windows 下统一使用 `rg -g '<glob>' -- <pattern> <paths>`。

### P-006 Docker Hub 基础镜像预拉失败

- 现象：`docker pull nginx:1.27-alpine` 在 Docker Hub 匿名 token 阶段报 `unexpected EOF`；本机到 `auth.docker.io:443` 和 `registry-1.docker.io:443` 的 TCP 探测均失败。
- 阶段：M3 Docker 构建前置。
- 影响：不能依赖外网刷新基础镜像；后端 `eclipse-temurin` 公共 tag 本地也不存在。
- 原因判断：当前 Docker Hub 网络不可达，不是 Docker daemon 故障；Docker/BuildKit 本身健康。
- 处理动作：按本机已配置的正式 primary mode=`offline-tar` 校验后端 tar SHA256 并加载固定 digest；前端固定 tag 的本地镜像已存在，记录实际 image id。未静默切换镜像、tag 或来源。
- 结果：后端配置 digest 精确匹配，前端固定 tag 可解析；允许进入构建，但继续记录 Docker Hub 不可达，不把 pull 失败隐藏为成功。
- 是否可前置检查：是，先核网络、配置 mode、tar/hash/digest 和每个 FROM 的本地 image id。
- 是否可自动化：是，构建预检应根据显式 base mode 选择 online pull 或 offline tar hash gate，并输出前端基础镜像固定 id。
- 下次如何避免：将前端基础镜像也纳入显式 digest/offline 资产契约，消除公共 tag 网络依赖。

### P-007 pnpm 10 默认阻止依赖构建脚本

- 现象：两个前端执行 `pnpm@10.25.0 install --frozen-lockfile` 后均报告 ignored build scripts；主程序前端涉及 `@parcel/watcher`、`@swc/core`、`core-js`、`core-js-pure`、`es5-ext`、`esbuild`、`vue-demi`。
- 阶段：M3 前端依赖恢复。
- 影响：若直接构建，依赖的本机二进制或生成文件可能缺失，构建结果不可作为可靠发布证据。
- 原因判断：pnpm 10 的依赖脚本审批策略未在冻结提交的 `package.json` 中声明，安装虽然退出 0，但会主动阻止这些脚本。
- 处理动作：仅在隔离 release worktree 中临时加入 pnpm 输出的精确 `onlyBuiltDependencies`，执行 `pnpm rebuild --pending`，确认 `pnpm ignored-builds` 为 `None` 后将 `package.json` 恢复为 HEAD。
- 结果：两个前端的 ignored-builds 均为 `None`，关键 `cross-env`、`vite`、`vue-tsc` 命令存在，两个 worktree 再次验证 clean；临时审批配置未进入源代码或发布提交。
- 是否可前置检查：是，安装后强制执行 `pnpm ignored-builds`，非 `None` 即阻塞构建。
- 是否可自动化：是，可在正式构建脚本中声明并锁定经过审查的 `onlyBuiltDependencies`，消除每次临时审批。
- 下次如何避免：把经评审的依赖构建脚本白名单提交到对应前端 `package.json`，并在 CI/发布预检中断言 ignored-builds 为空。

### P-008 PowerShell 插值变量紧邻冒号导致 ParserError

- 现象：两条诊断/配置脚本在双引号字符串中写 `$k:` 或 `$old:`，PowerShell 将冒号解释为变量作用域语法并在执行前报 ParserError。
- 阶段：M3 配置脱敏检查与隔离 local config 生成。
- 影响：失败发生在解析期，未读取或写出秘密、未修改配置、未触发发布动作；增加了一次重复命令和排查耗时。
- 原因判断：Windows PowerShell/PowerShell 的变量插值边界规则要求紧邻冒号时使用 `${k}` 形式。
- 处理动作：将变量改为 `${k}:`、`${old}:` 后重新执行，并验证 UTF-8 roundtrip、路径替换、环境禁用和 gitignored 状态。
- 结果：配置生成与安全断言全部 PASS，敏感值未输出。
- 是否可前置检查：是，复杂风险命令先过 PowerShell parser 或避免在命令内拼接自由文本。
- 是否可自动化：是，可将隔离配置生成固化为经过 parser 测试的脚本。
- 下次如何避免：双引号字符串中变量后紧邻 `:` 时一律使用 `${name}`；高风险配置命令先做只读 dry-run。

### P-009 主程序 Maven AI 模块依赖解析阶段长时间低吞吐

- 现象：`build-release` 的主程序 Maven 已完成多个模块 jar，随后 operation 日志因子命令缓冲不再增长；JVM CPU 增长很慢。只读 `jcmd Thread.print` 显示 main 线程位于 Maven Resolver `EnhancedLocalRepositoryManager.checkFind` 的 Windows 本地文件属性检查，进程仍 RUNNABLE。
- 阶段：M3 主程序后端构建。
- 影响：构建耗时明显增加；在 Maven 正常退出前不能确认发布包、manifest，也不能进入 test publish。
- 原因判断：线程栈显示 Maven 对本地仓库依赖图执行大量 Windows 文件属性检查；最终 Reactor 数据定位 `yudao-module-ai` 耗时 15 分 32 秒，`yudao-server` 打包 4 分 31 秒。并非网络下载、死锁、进程退出或 operation 丢失。
- 处理动作：不杀进程、不重提 operation、不切换构建来源；保留同一 operationId，结合 CPU、目标 jar 写入时间和 JVM 线程栈持续监控。
- 结果：同一 operation 未重试并正常完成，Maven 30/30 模块 SUCCESS，总耗时 25 分 18 秒。
- 是否可前置检查：部分，可在构建前做本地 Maven 仓库完整性/性能抽样并记录依赖解析基线。
- 是否可自动化：是，运行控制台可流式转发 Maven 输出并定期记录子进程心跳、阶段和最新产物时间。
- 下次如何避免：为发布构建增加 Maven 依赖离线预热与文件系统吞吐门禁，避免把输出缓冲误判为停滞。

### P-010 Vite 生产构建内存峰值过高

- 现象：主程序前端 `vite build --mode test` 运行中工作集峰值观测约 13.1 GB、私有内存约 14.1 GB，显著高于构建前基线并触发分页；子进程结束后物理/虚拟内存恢复。
- 阶段：M3 主程序前端构建。
- 影响：低内存机器存在 OOM、系统抖动或构建超时风险；本轮尚未因此失败。
- 原因判断：大型前端完整生产打包在转换/压缩阶段占用高峰，脚本虽设置 `NODE_OPTIONS=--max-old-space-size=8192`，进程私有提交量仍明显高于该堆上限，不能仅用 V8 heap 参数代表系统容量需求。
- 处理动作：保持同一构建进程，监控 CPU/工作集/私有内存和系统可用内存，不启动并行构建或其他高内存任务。
- 结果：`build:test` 成功，`dist-intruoyi-test/release-info.json` 生成，内存释放；发布未降级。
- 是否可前置检查：是，构建前核物理内存、提交限制和虚拟内存；构建中记录峰值。
- 是否可自动化：是，为构建 wrapper 增加 peak working set/private bytes 采集和容量阈值门禁。
- 下次如何避免：将发布构建安排在资源独占窗口，并对前端 bundle/插件做专门内存剖析；在未验证前不得通过降低压缩/跳过构建来规避。

### P-011 Dockerfile 后端基础镜像 ARG 默认值警告

- 现象：后端 Docker build 成功，但 BuildKit 报 `InvalidDefaultArgInFrom`，因为 `ARG ${BACKEND_RUNTIME_BASE_IMAGE}` 的默认值为空或无效。
- 阶段：M3 后端镜像构建。
- 影响：本轮显式传入固定镜像并解析到 digest `sha256:b4f7d85...`，不影响当前产物；若未来漏传 build arg，会在 FROM 阶段失败且错误可读性较差。
- 原因判断：Dockerfile 依赖调用方必传参数，但没有合法默认值，BuildKit 静态检查因此告警。
- 处理动作：本轮不修改冻结源码；核对实际 FROM digest 与离线基础镜像配置完全一致，并保留 warning。
- 结果：后端镜像成功生成，实际基础镜像 digest 正确。
- 是否可前置检查：是，Dockerfile lint 与 preview 必须断言 build arg 非空且 digest 匹配。
- 是否可自动化：是，给 Dockerfile 合同测试增加 ARG/FROM 校验。
- 下次如何避免：长期方案是为 ARG 提供受控合法默认值或在构建脚本进入 Docker 前显式 fail fast，并保留 digest 断言。

### P-012 发布日志中文编码显示乱码

- 现象：Maven warning 和 NAS share 的中文在 operation 日志/API 读取中显示为乱码，但命令路径、退出码、releaseTag 和最终状态可读。
- 阶段：M3 build-release 日志采集。
- 影响：降低人工审计可读性；若关键错误只有中文文本，可能延误定位。未影响脚本退出码、manifest 或产物内容编码。
- 原因判断：RuntimeControl 启动 UTF-8，而子进程仍使用 Windows PowerShell/Javac 的本地代码页，日志合并时编码边界不一致。
- 处理动作：发布结论只使用结构化 operation status、Manifest JSON、validator 和明确退出码；不根据乱码片段猜测成功。
- 结果：结构化证据全部 PASS，乱码作为独立问题保留。
- 是否可前置检查：是，构建前输出父子进程编码探针并验证中文 roundtrip。
- 是否可自动化：是，统一子进程 UTF-8 环境并增加日志 roundtrip 合同测试。
- 下次如何避免：运行控制台执行 Windows PowerShell/Javac 前显式统一输入输出编码，且 API 日志以原始字节按已知代码页解码。

### P-013 测试服现有热修运行态前后端版本不一致

- 现象：发布前 `.env IMAGE_TAG`、compose 解析和 backend 实际镜像均为 `hotfix-20260814-route-submit-order-r1`，frontend 实际镜像与 `/release-info.json` 仍为 `release-20260813-intmain-head-test-r260812b-r2`；最近数据库 release lock 为 r260812b-r2=`APPLIED`，没有该 hotfix 的正式发布锁。
- 阶段：M5 测试服写入前只读基线。
- 影响：测试服当前不是单一可追溯 releaseTag，普通 compose restart 可能把前端切到缺少 release-info 证据的 hotfix tag；若不记录，发布后无法区分本轮收敛与既有漂移。
- 原因判断：证据符合后端热修只更新 `.env`/backend、未以完整发布链重建前端与 release lock 的状态；无 RUNNING lock 或活动发布进程，未发现本轮并发发布。
- 处理动作：不手工修改 `.env`、容器或数据库状态；冻结完整前置快照，本轮仅通过已授权的完整 `publish-test` 正式动作把 backend/frontend/release-info/lock 收敛到同一目标 releaseTag。
- 结果：publish-test 在 required SQL 阶段失败；`.env`/Compose 已指向目标 tag，但实际 backend/frontend/release-info 未切换，符合失败后部分漂移门禁。本轮已停止并标记 blocked。
- 是否可前置检查：是，发布前强制比较 `.env`、compose、backend/frontend 实际镜像、release-info 和 latest lock。
- 是否可自动化：是，运行控制台 preview 前可输出结构化 drift report 并标注 `partial-hotfix`。
- 下次如何避免：热修也必须生成可追溯 releaseTag 和完整 backend/frontend/release-info/lock 证据，禁止只改 `.env` 或单容器后留下长期漂移。

### P-014 publish-test preview 本地断言 helper 误用了 PowerShell 自动变量 `$args`

- 现象：首次 preview 响应本身包含正确参数，但本地 `ArgValue` 函数内的 `$args` 被 PowerShell 解释为函数自动参数，导致 Mode/Environment/ServerHost 等读取为空并触发本地断言失败。
- 阶段：M5 publish-test preview。
- 影响：仅为本地验证假阴性；preview 无写操作，未提交 publish-test、未修改测试服。
- 原因判断：函数作用域中的 `$args` 覆盖外层同名变量。
- 处理动作：保留原 preview JSON，改用 `$previewArgs` 并按索引直接读取后重新验证。
- 结果：结构化 preview 全部 PASS，目标仅为 test 172.30.30.58；未重新提交或绕过 preview。
- 是否可前置检查：是，PSScriptAnalyzer/合同测试可禁止把自动变量名当业务变量。
- 是否可自动化：是，将 preview 字段断言固化为测试脚本。
- 下次如何避免：PowerShell 中禁用 `$args`、`$input`、`$matches` 等自动变量名作为持久业务变量。

### P-015 本机 OpenSSH 退出时输出 pending socket warning

- 现象：多次 SSH 只读命令退出码为 0 且远端输出完整，但 stderr 追加 `close - IO is still pending on closed socket`。
- 阶段：M5 测试服只读预检。
- 影响：若只扫描 stderr 文本可能误判命令失败；当前未丢失 stdout，退出码为 0。
- 原因判断：本机 Windows OpenSSH/异步管道关闭时序提示，不是远端命令错误；仍需通过退出码和完整标记校验，不能静默忽略未知 stderr。
- 处理动作：后续长脚本固定用 UTF-8 LF bytes stdin，要求远端脚本 `set -euo pipefail`、完整开始/结束标记和 SSH exit=0；该已知 warning 单独记录。
- 结果：schema、lock、migration、镜像和 release-info 输出完整，SSH exit=0。
- 是否可前置检查：是，最小 SSH probe 可验证是否存在该客户端行为。
- 是否可自动化：是，封装 SSH runner 对此精确 warning 分类，同时任何其它 stderr 或非零退出码仍 fail fast。
- 下次如何避免：使用统一二进制 stdin SSH wrapper，并升级/修复 Windows OpenSSH 后移除精确例外分类。

## Long-running Review

- 当前进度：M5 阻塞。
- 已完成：M1-M4。冻结与隔离、经验门禁、维护控制台构建、唯一 build operation、发布包/镜像/NAS 上传、Manifest v1/sourceRepos/release-info/changeSet/洁净度验证均 PASS；publish-test preview PASS，并只提交一个测试服 operation。
- 阻塞点：required SQL `20260813_form_template_menu_before_form_center` 因菜单真实父级仍为 1186 而不是 990200 失败；release lock 已标记 FAILED 且无 RUNNING lock。
- 耗时原因：主程序前端 pnpm 缓存链接 1103 包耗时 26 分 44 秒；Maven `yudao-module-ai` 15 分 32 秒、`yudao-server` 4 分 31 秒；Vite 内存峰值高；publish-test 上传 490 个 required SQL 并逐条登记 435 个状态后才在 live-state 前置断言失败。
- 下一步：保持失败现场和两个 release worktree，不重试、不清理；先由正式源码修复 code-only 迁移依赖闭包并补测试，提交后冻结新 HEAD、构建新 releaseTag，再重新执行完整测试服发布。

### P-016 code-only 跳过 data 迁移导致后续 menu 迁移真实前置不成立

- 现象：唯一 publish-test operation=`op-2026-08-15T183354112639300Z-271fd4fe-4a9c-456d-93e4-bc3a14ae3c4f` 最终 `FAILED`；`20260813_form_template_menu_before_form_center.sql` 第 147 行报 `Missing form center parent menu 605071200 under global basic data`。
- 阶段：M5 测试服 required SQL。
- 影响：本次目标镜像未部署，测试服仍运行旧 backend/frontend；目标 release lock=`FAILED`，迁移计数为 APPLIED=6、SKIPPED_ALREADY_APPLIED=428、FAILED=1。本次发布不能判成功，M6 页面/控制台成功验收与 M8 清理均不得执行。
- 原因判断：真实菜单 `605071200` 存在但 `parent_id=1186`（流程管理），不满足要求的 `parent_id=990200`（基础数据）。Manifest 将负责移动菜单的 `20260721_form_center_menu_under_basic_data` 标为 `type=data`，code-only 发布按规则跳过；两个 20260722 `type=menu` 迁移虽依赖它，却因迁移台账判定已应用而跳过，20260813 menu 迁移最终用 live-state 断言暴露台账与真实结构漂移。现有 metadata gate 只验证依赖 ID 存在和类型合法，未验证 code-only 过滤后的可执行依赖闭包与关键真实状态。
- 处理动作：立即停止且不重试；用只读探针核 release lock、migration 状态、实际菜单父级、`.env`/Compose 与实际镜像、health/HTTP/release-info；保留失败 worktree/state。未手工修改菜单、migration ledger、容器或镜像。
- 结果：release lock=`FAILED`、RUNNING lock=0；`.env`/Compose 为目标 tag，实际 backend=`hotfix-20260814-route-submit-order-r1`、frontend/release-info=`release-20260813-intmain-head-test-r260812b-r2`，旧服务 health/HTTP 正常但目标版本未上线。
- 是否可前置检查：是。build-release 前对 `publishScope=code-only` 计算过滤后的迁移依赖闭包；任何可执行迁移传递依赖被过滤的 `type=data` 时必须阻塞，并对 SQL 中显式 live-state 断言生成远端只读预检。
- 是否可自动化：是。在 policy gate/合同测试中增加 `executable -> skipped data` 依赖闭包规则，并从 menu/config/permission SQL 的固定 ID/parent/path 断言生成预检 SQL。
- 下次如何避免：从正式源码修复迁移类型或拆分为结构/菜单迁移，补 BDD/TDD 后提交；用新冻结 HEAD 和新 releaseTag 重建。禁止手工补测试库、改 ledger、修改失败包或复用失败 tag。

- 阻塞审计补充：发布包 `preflight-plan.json` 为 `passed`。其中 `20260721_form_center_menu_under_basic_data=APPLY`、两个 20260722 中间菜单迁移=`SKIP_ALREADY_APPLIED`、`20260813_form_template_menu_before_form_center=APPLY`；随后 `Get-ReleasePreflightApplyItems` 才按 code-only 删除 data APPLY 项，未对剩余节点重新计算传递依赖。
- 范围审计：Manifest 490 个迁移中有 42 个非 data 迁移包含 data 祖先；结合本次 target-state 后，仍有 3 个待执行迁移依赖 pending 且会被过滤的 data 祖先。除表单中心两条外，`20260813_mes_process_pool_event_revision_nullable_work_order` 还传递依赖 pending 的 DCC 产品目录 data 清理；手工处理首个菜单也不能证明后续安全。
- 正式修复面：主程序 `script/release/release_preflight_plan.py` 及测试需要感知 publishScope；维护副本、`publish-int-ruoyi.ps1` 和合同测试必须同步；表单中心迁移类型与 MES foundation 的跨域 dependsOn 需要分别做正式元数据修复。任何方案均会产生新提交和新 releaseTag。

RED: publish-test `op-2026-08-15T183354112639300Z-271fd4fe-4a9c-456d-93e4-bc3a14ae3c4f` -> FAIL, `20260813_form_template_menu_before_form_center` 的 live-state 前置不成立。

### P-017 迁移根因搜索范围过宽导致诊断输出截断

- 现象：一次 `rg` 同时扫描冻结源码、发布包和任务归档，命中大体积历史 SQL artifact，输出超过 1 MB 并被截断。
- 阶段：M5 失败根因定位。
- 影响：没有修改文件或远端，但增加诊断噪声并延迟获取关键文件头。
- 原因判断：搜索模式包含通用中文词和固定菜单 ID，且未把 `doc/tasks/**/artifacts` 排除。
- 处理动作：改为只读冻结目录 `IntRuoyiBackend/sql/mysql`，再用结构化 JSON 解析 Manifest 的 `migrationPlan`。
- 结果：精确确认 20260721=`type:data`、20260722/20260813=`type:menu` 及 dependsOn 链。
- 是否可前置检查：是；先列文件和 JSON schema，再限定目录与字段。
- 是否可自动化：是；为迁移 gate 输出最小依赖链，不依赖全文检索。
- 下次如何避免：搜索迁移根因时排除任务归档和构建 artifact，结构化数据优先用 JSON parser。

- 复发记录：后续一次检索再次把 `--glob` 排除项放在路径之后，Windows `rg` 将其解释为路径并扫描了历史任务大文件，输出再次截断。已停止使用该方式；本轮最终依赖分析仅使用 `manifest.json`/`preflight-plan.json` 的 JSON parser 与明确 SQL 文件路径。该复发说明应把安全搜索封装为固定命令而不是依赖人工记忆。

### P-018 operation 原始日志包含展开后的数据库凭据

- 现象：publish-test operation 的 `Run:` 行记录了展开后的 MySQL 命令参数，包含明文数据库凭据；失败信息也会把远端 stderr 写入 lock/migration error_message。
- 阶段：M5 operation 监控与失败记录。
- 影响：原始 operation log 不允许复制到任务目录或提交；若直接把长 tail 作为证据会泄漏凭据。
- 原因判断：发布脚本在日志层记录了执行前已完成变量展开的命令，脱敏发生不完整或晚于日志输出。
- 处理动作：后续轮询只输出 operation status、log length 和已脱敏阶段摘要；本任务不复制、不提交原始 log，结构化证据只保留 releaseTag、operationId、状态、计数和脱敏错误摘要。
- 结果：任务文档与待提交证据不含明文凭据；原始秘密日志仅留在本任务外部 state 目录并因任务阻塞暂不清理。
- 是否可前置检查：是；发布前对 logger/redactor 做包含 `mysql -u... -p...` 的自测。
- 是否可自动化：是；命令在结构化参数层脱敏后再格式化，任务证据生成器拒绝 secret pattern。
- 下次如何避免：禁止记录展开后的 secret-bearing command；只记录命令模板和脱敏参数，原始 stderr 进入 operation 前统一过滤。

### P-019 `ssh -n` 与 stdin 脚本承载互斥

- 现象：第一次只读失败态探针同时使用 `ssh -n` 和 Python stdin bytes，SSH 退出 0 但远端未执行脚本，只返回 pending socket warning。
- 阶段：M5 失败后只读核对。
- 影响：产生一次空探针和重复操作；没有远端写入。
- 原因判断：OpenSSH `-n` 将 stdin 重定向到空设备，与 `bash -s` 通过 stdin 传脚本的用法互斥。
- 处理动作：移除 `-n`，保持 UTF-8 LF binary stdin、`bash -s`、`set -euo pipefail` 与完整标记后重跑。
- 结果：第二次探针 exit=0 且完整返回 lock、migration、menu、镜像、health、HTTP 和 release-info。
- 是否可前置检查：是；SSH wrapper 根据是否传 stdin 自动禁止 `-n`。
- 是否可自动化：是；封装互斥参数合同测试，并要求预期标记非空。
- 下次如何避免：无 stdin 的一次性命令可用 `-n`；`bash -s`/heredoc/binary stdin 载荷禁止 `-n`。

GREEN: failure-state-readonly-audit -> PASS；发布锁已失败并释放、RUNNING lock=0，失败迁移与菜单父级、版本漂移、旧运行态健康均已结构化确认；未修改测试库或重试发布。

### P-020 主维护控制台本地配置仍指向废弃主程序路径

- 现象：准备停止本任务 48181 隔离控制台并恢复主维护路径时，只读检查发现主目录 `config/runtime-control.local.yaml` 的 `repo-root=D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro`、`frontend-root=D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3`，与项目强制的 `E:/IntRuoyi/IntRuoyiBackend`、`E:/IntRuoyi/IntRuoyiFronted` 不一致。
- 阶段：M5 失败后运行环境恢复预检。
- 影响：直接用主配置重启 48181 会让后续 preview/build 指向错误源码根；无法证明恢复后的控制台符合当前项目契约。
- 原因判断：主目录本地配置未随主程序根目录/子目录命名迁移同步更新。
- 处理动作：fail fast，不停止当前 task-owned 48181 隔离控制台，不用旧配置启动主控制台，不修改本地配置；保留 release worktree/state 以保证当前进程路径有效。
- 结果：48181 仍 health=UP 且进程命令行指向 `D:/IntRuoyiWorktree/r260816a/m`；任务继续 blocked，未进行 worktree/state 清理。
- 是否可前置检查：是；每次接管/恢复 48181 前结构化比较 repo-root/frontend-root/ops-root/state-dir 与项目固定路径。
- 是否可自动化：是；start/restore 脚本加入路径契约断言，任一旧目录命中即拒绝启动。
- 下次如何避免：由独立正式任务修正主本地配置并验证 preview/health/release-status，再恢复主控制台；不得在发布失败收尾中临时绕过。

GREEN: blocked-task-record-verification -> PASS；`publish-test-operation-final.json`、`remote-failure-state.json` 及既有 manifest/source evidence 均可解析；任务与经验文档 UTF-8 无 BOM；`git diff --check` 通过；本任务新增/修改内容严格凭据扫描 0 命中。

BLOCKER: test-only-release -> `publish-test` 未成功，目标镜像未运行；必须正式修复 code-only 迁移依赖闭包并用新提交、新 releaseTag 重建。失败 tag、部分迁移记录、release worktree/state 和 48181 隔离控制台保留，未提交、未清理。

BLOCKER AUDIT 2: frozen-input-supported-path -> NONE；同一 releaseTag 重试会复现确定性失败，修改包/manifest/SQL/ledger 会破坏冻结输入契约，with-data 属于不同发布范围且会执行未授权业务数据迁移，手工应用首个 data SQL 仍不能消除第二条 pending data 依赖链。

- Scope 证据：目标 Manifest 固定 `publishScope=code-only`、artifactCount=500、database dump=0、MinIO snapshot=0；`Assert-DeployReleasePackageArtifactsForScope` 对 with-data 强制要求 MySQL dump、MinIO snapshot 和 DCC object inventory。因此同一包不存在受支持的 with-data 变体，修改 scope 会同时违反包契约和冻结来源验收。

### 正式修复 BDD/TDD 草案（未授权实施）

BDD: code-only 在远端写入前阻塞 pending data 依赖 -> Given target preflight 将 data ancestor 标为 APPLY，intermediate migration 已应用，descendant 非 data migration 为 APPLY / When 生成 code-only preflight plan / Then plan=`blocked`，返回最小依赖路径且不修改 `.env`、release lock 或 migration 状态。

BDD: 已应用 data 祖先不被误判为 pending scope blocker -> Given data ancestor checksum 匹配且 target state=APPLIED，descendant 为 APPLY / When 生成 code-only preflight plan / Then scope dependency gate 不因该祖先阻塞，仍保留 SQL 自身 live-state precondition。

BDD: 发布脚本不得在 passed plan 后静默删除依赖节点 -> Given preflight plan 含 pending data APPLY 和依赖它的 APPLY descendant / When PowerShell 准备 required SQL 执行集合 / Then fail fast 并输出脱敏最小路径，不得只记录 `Skipping data required database SQL` 后继续。

RED 目标：主程序 `script/tests/test_release_preflight_plan.py` 增加直接/传递 pending data ancestor、intermediate SKIP_ALREADY_APPLIED、already-applied data ancestor 三组测试；维护 `tests/test_code_only_required_sql_contract.py` 增加 publish-scope 透传和过滤后闭包断言；现状应先失败。

GREEN 目标：主程序/维护 preflight plan 与 blocked action 集合同步，PowerShell 不再后置静默破坏依赖图；表单中心 type 与 MES foundation 跨域 dependsOn 经独立 SQL 合同测试修正；全量 migration policy、preflight plan、PowerShell parser 和 code-only required SQL 回归通过后才能提交新 HEAD。

BLOCKER AUDIT 3: unchanged-frozen-release-state -> CONFIRMED；operation 仍 `FAILED`，测试服 target migration 仍 APPLIED=6/SKIPPED_ALREADY_APPLIED=428/FAILED=1、RUNNING lock=0，菜单 605071200 仍为 parent_id=1186；实际 backend/frontend 仍为旧版本。维护/app worktree 分别保持 `3cd1f3e7...`、`cb0464ce...` 且 dirty=0，Manifest 仍固定 code-only；无外部修复或状态变化可解除阻塞。

BLOCKER FINAL: 该相同阻塞已跨原始发布轮及两次连续恢复复核重复 3 次。没有用户授权的新提交或外部状态修复时，无法继续实现目标；按目标状态规则正式标记 blocked，保留全部现场且不执行无效重试。
