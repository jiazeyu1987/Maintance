# Spug 只读挂载配置发布修复与明确续办

## Goal and current status

in_progress。三资源真实安装已 PASS；v2 配置发布实际 exit1，停在 spug-publish。四个 preflight 与三服 host-publish 均真实 PASS（57六个、58三个、59三个 selector）；Spug 阶段 completedWrites=0，错误为 Errno30，拒绝创建 /run/intruoyi-spug/intruoyi-program-selections-45dd7dc-r6.private.json。原 FAILED/请求/原件全部保留，不自动重跑 v2。

实际 Docker inspect：/run/intruoyi-spug 是 C:/Spug/runtime/private 的只读 bind；/opt/intruoyi-spug 也是只读 bind，资源已通过宿主侧正式路径更新；/var/lib/intruoyi-spug 为可写 named volume。问题是部署工具对配置写入位置的假设错误，不是业务程序或三服恢复失败。不得改挂载为可写，也不重启容器。

## Milestones and expected verification

1. 按项目重构工作流由子代理审查并提出最小正式合同和 BDD。范围只限本任务发布工具/必要读取器、专属测试/文档；产品资源、45/r6控制代次及既有构建/安装输入冻结。
2. 先形成真实失败测试：实际只读配置挂载的合同、宿主绑定路径精确映射、旧配置先保全、文件/目录别名/漂移/未知写入状态、失败不重试；再最小正式实现及相关回归。不能只让 fixture writable 后称通过。
3. 发布器通过已核实际 mount Source/Destination/RW 和固定18080/18081身份，映射到唯一宿主配置目录；只在宿主路径原子更新明确列出的配置/连接，并从原容器实际读回。所有原件在首写前独占保存并验证，不能在只读容器目录写入或移除 ro 保护。
4. 原 r6 已部分发布，续办必须显式引用原 FAILED 的准确 pin、阶段完成事实和新的当前只读观察；不能覆盖原 v2 rich/core/attempt、不能重跑已成功服务器写入。必要时新增正式版本化的 publication attempt/continuation 合同，保留同一个控制代次 r6，不能为了绕过失败虚构 r7 控制代次。
5. 新核心必须核全部原阶段和续办真实原生结果，且独立证明 selector、配置/任务/历史、业务/挂载/fstab/18081保护；不以原7阶段PASS补造完整成功，不伪造原spug-publish通过。固定最终代码/测试pins并父独立验证、限定实现提交后，才进行实际续办。
6. 完整UI及三服实际恢复仍独立验收；当前未执行新备份/恢复，目标保持in_progress。

## 父审查与最小实施批准

已完整审查 spug-readonly-bind-publication-design.md（19419B，SHA c071925d508f8deeee088c55d25e9222e2f75128b7b4c79c48b236838bdacba5）。批准按该设计先 RED 后 GREEN/REGRESSION；仅新增 continuation 模块/专属测试，并解冻 publication.py 的原 verify 深校验纯函数提取、installation_selection.py 与 observe_closeout_hosts.py 的严格 v3 分派。原 v2 publisher、远端 HOST/SPUG 程序正文、产品资源及控制代次保持。project_core 通过原 v2 绑定上下文复用，不扩大原字段合同。

所有七项保全后才按原顺序逐项安装；宿主五项、容器 volume 两项，最后 bridge。实际 mount 与原运行器终态机器证据由父补齐，缺证据必须拒绝 prepare/apply，不能先写占位 PASS。宿主原子写用真实文件测试，不把单元传输 fixture 称为现场通过；Windows 无目录 fsync 的事实如实记录。实际发布仍由父在实现提交及必要独立验证后执行，本批准不允许子代理操作 Docker/服务器或提交。

原源码历史闭包补充：原attempt固定286个inputPins，其中本次改变的历史源只有publication.py和installation_selection.py；运行根下七个待改配置及产品资源不在该不变闭包。批准v3唯一originalSourceCustodyPin，严格映射这两份旧原pin到独占保留的同字节副本；其余284项仍逐原路径完整核验，旧v2 publisher不得映射。父在任何实际续办前独立读回两份保全并形成正式custody，新的执行源码另行固定，不修改原attempt或原pin。

### 设计约束检查（沿用）

- 是否引入 fallback/降级/吞异常：否。显式宿主部署路径和版本化失败续办；任一未知/漂移拒绝，不自动回退。
- 是否从根因和长期维护角度解决：是。将只读容器的运行时读取与正式宿主配置安装分开，保持只读挂载。
- 是否存在临时补丁或绕过：否。不执行临时手工复制，不改旧失败、原mount或产品安全检查。

## 经验门禁

- Trigger：实际发布在只读 bind 写前失败并已有三服部分成功。
- Preflight check：原八阶段/完整错误与实际挂载、旧/新配置及审计路径实际状态、同一控制代次和已安装资源、任务/受保护实例固定。
- Blocker：缺原失败pin、路径或mount歧义、无法判明已写状态、需要覆盖原记录或重跑已完成服务器发布。
- Verification：RED→GREEN→REGRESSION，实际Linux只读挂载或原容器只读观察证明、宿主临时真实文件行为测试、父独立验证、正式原始续办/核心证据。
- Forbidden action：不改容器权限或挂载，不重启Docker/容器，不修改业务/NAS/fstab，不改旧报告、归档、控制代次或冻结构建，不派发备份恢复，不盲重试v2。
- Evidence：main-program-spug-installation-45dd7dc-r6.private.json 及八阶段原件、spug-publication-45r6-after-delta838-r1.completion.private.json、实际挂载inspect与后续专属TDD记录。真实续办写入前另记 experience-preflight。
