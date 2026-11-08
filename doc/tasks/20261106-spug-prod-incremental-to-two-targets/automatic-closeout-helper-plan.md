# 自动增量验收与收尾 helper 重构

## Current Status
ready_for_closeout — TASK helper 实现及本机合同验证完成，交父任务实际验收。未执行删除、服务器写入、浏览器、提交或合并；自动 FULL→I1→I2、当前58/59控制和目录UI证据尚需父任务现场结果，整体任务不能据本机测试标完成。

## 目标与里程碑
- M1：固定证据合同，区分原367及58/59恢复时不可变代次与本轮当前控制；建立明确任务构建清单。
- M2：先写行为测试并 RED，再最小改造 verify_closeout.py、cleanup_owned_build.py、verify_stable_controls.py；必要共享纯核验函数留在 TASK。
- M3：仅本机验证真实已落盘原件及负向变异，不执行清理或远端操作；交父任务实际高风险预检和收尾。

## 里程碑与证据
- M1 已完成：历史367及恢复时旧代次保留；明确10代构建清单（最后一代 b5c8817 显式 register）；59原始两次 FAIL 逐字节pin保留，实际r3/372 PASS另选。
- M2 已完成：closeout_contracts.py 负责不可变证据合同；catalogue_current_verification.py 负责当前目录进程/文件/配置与原309任务；三个收尾入口使用显式清单、当前证明和自动三点源恢复合同。
- M3 已完成（仅本机）：原8项PASS；新增59选择/目录完整性先RED缺合同→GREEN；旧367不可替代自动源恢复先RED→GREEN；真实目录首轮FAIL不可选先RED→GREEN，最终12项回归PASS。另Python及内嵌Linux载体compile/AST、目录helper node --check通过。
- 精确步骤见 automatic-closeout-helper-usage.md；初版回归原文及受测SHA见 automatic-closeout-helper-regression.json/.txt。r3真实登录准备增加2项认证合同测试，RED→GREEN后12+2=14项回归及新SHA见 automatic-closeout-helper-regression-r2.json/.txt。
- 未验证范围：未执行新的当前控制核验、真实自动三点收尾、任何worktree清理。父任务目录首轮已真实FAIL，必须保留并用独立r2验证；本子任务只准备并检查helper语法。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；缺少最终自动链、安装、构建或观察证据即失败，不能沿用旧 PASS。
- 是否从根因和长期维护角度解决：是；用明确证据身份和清单取代硬编码数量与最晚文件猜测。
- 是否存在临时补丁或绕过：否；原失败与恢复时的安装证明保持，不重写成当前代次。

## 经验门禁
- Trigger：任务扩大到自动链及新控制代次，旧收尾脚本仅认7个构建和旧控制。Preflight check：显式构建/安装证据清单及完整 SHA、原失败观察 pin、真实成功观察和时间顺序。Blocker：证据缺失、漂移、未验收、无明确归属。Verification：真实本机原件读取与定向篡改拒绝，清理检查须路径/注册/原提交/干净含ignored/进程/独占任务容器齐全。Forbidden action：不得glob搜索后删除，不将原367或恢复时安装改写成新代次，不覆盖失败记录。Evidence：本计划与子测试报告。
- 原控制安装活动回执必须逐代保留 previous/current pin 链；恢复时证明和当前控制证明分别核验。
- 清理前父任务 execution-log 必须记录经验预检 PASS，任务状态 ready_for_closeout；helper 重构阶段仅检查，不触发删除。
- 验收与清理按明确任务资源归属，不操作其它任务工作树/进程/控制台。

## BDD
- Given r3真实登录与身份已通过，但新iframe地址仍为空；When r4点击菜单后检查备份文档；Then 先等待精确 `/backup-restore/?embedded=1` 导航达到 domcontentloaded，再解析URL和验证document200，期限仍45秒，错误目标或文档失败继续拒绝；前三次FAIL原件保留。
- Given 目录r2实际仍为登录页，且按钮为“登 录”；When r3显式 `--login` 以全新浏览器context执行真实登录；Then 精确沿用自动FULL的账号/密码选择器、私密凭据路径、嵌套data/MFA/安全提示合同，只有本机精确 `/api/account/login/` 单次认证POST可发出，authPosts单计；所有业务写入阻断，仍核管理员、菜单、完整目录，不再重试旧session。
- Given 目录首轮使用旧公共会话停在登录页而零业务POST；When 显式 r2 选择自动FULL实际成功登录保存的会话；Then 不覆盖首轮attempt/result，仍从平台核对管理员及侧栏权限，过期明确失败；后续成功观察必须另以失败原件pins+selected证明绑定，不延长超时或绕过身份检查。
- Given 目录安装已真实 PASS，但安装探针仅返回 items=0/refreshing=true；When 独立真实浏览器从已登录 Spug 进入“全部包清单”并刷新；Then 只有 document/目录 HTTP 200、非空且 refreshing=false/complete=true、无错误、可见表格行与总数一致、零业务 POST 才可验收；初始空缓存和59 r3仅HTTP200不能替代该证据。
- Given 每个自动点已审计成功；When 收尾核来源恢复；Then 必须匹配同 operation/source/安装提交的独立来源恢复报告，原全局状态、Redis、五服务、语义健康、锁和worker归零；FULL/I2要求10044份失败原件全SHA，I1明确只核状态。
- Given 58r4 或59的原只读终态失败后有独立成功观察；When 选择成功观察；Then 所有失败文件逐字节 pin 保留，所选原件匹配同一恢复请求，时间顺序及成功证据完整，不能用后一次覆盖前一次。
- Given 显式任务构建清单登记9代及后续目录修复代；When 检查或选择清理代次；Then 仅接受清单中精确路径/提交/报告/package身份，数量随清单变化，未登记路径和清单重复/遗漏即拒绝。
- Given 新自动 FULL→I1→I2；When 收尾；Then 三次真实 UI 唯一请求、根/父链、成功原生点及 source恢复、最终当前计划均一致；历史367链仍独立通过。
- Given 58/59恢复采用旧控制且随后授权安装新控制；When 核当前稳定路径；Then 历史安装证据不变，另核新安装文件及活动回执/epoch/进程和源/Spug/目录代次，缺任一项不能PASS。
