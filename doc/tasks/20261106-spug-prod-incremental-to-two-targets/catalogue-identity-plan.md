# 包清单轻量身份与有界桥接修复

## Current Status
ready_for_closeout — Windows66/Linux15回归通过，正式实现已由根任务限定提交 b5c8817；专属干净构建及安装prepare通过，待根任务协调apply及真实页面验证。本子项未重载运行服务，不执行新备份恢复。

## 目标与已证实根因
真实 18080 nginx 在两次恢复终态页面的包清单 GET 等待 18111 响应头超过 30 秒。18111 每次先读 18112 `/state` 做身份校验，实际 81,281,836 字节，其中历史 jobs 占 79,330,982 字节；独立容器测量 9.991 秒中 `/state` 传输占 9.312 秒，清单本身仅约 0.009 秒。失败瞬间没有分段计时，因此不伪称已证实当时各段耗时。实际清单缓存不依赖已停用的备份来源。

修复采用认证后的独立 `/identity`，从已校验的固定 executor 配置生成常量大小响应；不读取历史、不获取状态锁、不进行远端轮询。保留 `/state` 现有 API 和历史原件。bridge 严格核 schema 和 app id，固定 origin、拒绝重定向，不因 identity 缺失回退 `/state`。展示 repo 与执行器实际 repo 当前本来不同，不新增猜测路径白名单；身份响应可记录实际 repo 供审计，不携带凭据。

## 正式源码归属和范围
当前工作区为 Maintance 仓 `codex/spug-selectable-restore-targets-20261104`。18112 运行的 `C:/SpugHandoff/release/source` 是无 Git 迁移快照；旁边 repository 是 IntRuoyiAll 的 portable-release 分支，不能当维护仓。

Maintance 已提交 `8bd2270` 的 `package_catalog.py` 和 `package_presence.py` 与运行文件归一 LF 后逐字节一致，SHA 分别为 `335b06af178da3e64456ed1c96843387b42ed7031dc56f0c02864aeb515fc7a7`、`a4cc271309ece2b681f9a239cc8a43e0df658c09a17d862a50b02fba792da7ec`。精确移植这两个模块、原两份测试和对应目录路由/服务器接入；保留当前 current-versions/database-versions。最终对比实际 executor 还确认其已运行 `git log --all --date-order`，为避免安装回退，经根任务确认追加同一 `8bd2270` 的此一行和 `test_commit_catalog.py`（原始提交 `74b9614`）；该真实 Git 测试先 RED 再 GREEN。

新增修复范围：`application_registry.py`、`executor.py`、独立有界 HTTP 模块与 `test_release_identity.py`。后台目录最小状态投影不属于本次最小根因修复；现有后台扫描原行为保持。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。身份失败/不支持/错误 origin/超限/期限耗尽均明确失败；不转发后续动作、不返回伪空目录。
- 是否从根因和长期维护角度解决：是。去除目录请求与全历史大小的耦合，使用整个桥接调用共享期限和有界正文，保持真实身份校验。
- 是否存在临时补丁或绕过：否。不加长 nginx，不清理历史，不修改运行快照或业务配置。

## 经验门禁
- Trigger：实际页面包清单连续 504，需修复调用链并恢复已经运行的正式目录能力。
- Preflight check：精确 18080 容器与 18112 源路径/源码 Git 同源摘要；保存实际错误、80MB 状态和两个目录根计数；身份鉴别和原历史保持。
- Blocker：源码归属不明、目录模块不一致、真实测试未通过或安装目标包含无关 18081，禁止安装。
- Verification：真实本地 Executor/SQLite/HTTP、保持原状态 API、身份认证和错误来源拒绝、实际网络慢正文/超限/重定向注入、相关回归；根任务协调干净提交与最终真实页面。
- Forbidden action：不得把网络模拟成功冒充真实 E2E；不得重定向密钥、回退读取历史、直接复制整个运行快照或删除历史来缩小响应；本子项不改运行服务。
- Evidence：`catalogue-504-runtime-route.json`、`catalogue-504-upstream-timings.json`、`catalogue-504-bridge-timings.json`、本子项 RED/GREEN 输出。

## BDD
1. Given 真实本地 Executor 带大量旧历史且状态锁被占用，When 认证读取 identity，Then 小响应立即返回且未读状态；错误密钥仍拒绝。
2. Given 独立真实 Executor 和包清单接口，When registry 读取清单，Then 只请求 identity 和清单，不请求 state，原 state API 内容仍可读取。
3. Given 错误应用、未部署 identity 或 HTTP 重定向，When bridge 校验，Then 明确拒绝且不发送目标请求、不回退 state、不转发密钥至另一 origin。
4. Given 身份与后续响应分段耗时，When 总期限耗尽，Then 失败时间受共享总预算约束；持续小字节返回不能不断重置期限。
5. Given 过大 Content-Length、未声明长度的大正文或错误 HTTP 响应，When 读取，Then 有界拒绝或保留真实错误状态，不能无界分配内存。

## 里程碑与验证
- [x] 只读诊断、生产同源 Git 基线、方案与范围。
- [x] RED：原3条真实本地HTTP测试失败：身份409、目录未登记、实际请求/state。
- [x] GREEN：精确基线移植及最小正式实现；慢header与全分支提交另外各先RED后GREEN。
- [x] REGRESSION：Windows66条、Linux15条全部通过，零skip；独立Linux容器已删除。
- [ ] 根任务协调提交/部署/真实页面；本子项不单独部署。

## 验证与安装准备结果
`catalogue-identity-regression.json` 固定Windows八测试模块、候选SHA和sourceUnchanged=true；日志记录66tests/23.460s。`catalogue-identity-linux.json` 固定Python3.12.15/git2.39.5镜像、network none、只读快照、15tests/7.408s、零skip、容器已移除。

`install_catalogue_identity.py --commit b5c8817de2b4cc5efdad566f0fb65fdabefcb8d8 --worktree PRIVATE/release-b5c8817` 已运行prepare-only，`catalogue-identity-install-plan-b5c8817.json` 为PREPARED，runtimeWrites=0。原空闲进程和完整history保持、SQLite一致备份、源码原件/配置及受保护组件pins已固定。apply还会核新进程exe/argv/cwd及新PID、安装文件逐项等于committed_inputs，并保存bridge startTime；安装报告不存在时不得宣称修复已上线。
