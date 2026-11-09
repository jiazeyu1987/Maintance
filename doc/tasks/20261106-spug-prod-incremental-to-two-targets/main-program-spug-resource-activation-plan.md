# 目录绑定资源的精确安装

## Current Status

v1 设计保留，完整任务 in_progress。产品候选 c7728ad 的独立资源构建及96项真实测试证据已产生；现场观察发现相对现网还缺两份先前已提交的 UI 资源。此次安装使用 spug-resource-deployment-delta-plan.md 的显式 v2 三文件部署差异，原 build/test 报告不改。v1 继续仅允许 adapter；下文保留其原设计边界。实际安装仍须新鲜观察及完整前后验证。

## 目标、里程碑与预期验证

从旧install_automatic_spug的11资源整体安装流程重构一个本次精确资源安装入口，复用publication模块的真实资源构建/测试pins验证。仅更换本任务18080实例绑定目录中的smallapp_adapter.py；其余10资源、三配置、全部连接、任务历史和18081原样保持。只精确重启本任务entry进程，不重启nginx/容器。adapter对未声明selectionConnections的旧配置兼容，通过安装后真实读取原配置和原目录证明；新目录配置由独立publication发布。

1. Subagent先写BDD和真实RED，再最小实现prepare/apply、比较后替换、独占保全与失败保留；局部GREEN/相关旧合同回归。
2. 父任务从真实已提交UI资源worktree与实际测试生成MainProgramSpugResourceBuild/v1；工具复用publication.validate_resource_build逐SHA核验，不创造假的release-build控制包记录。
3. 对精确18080和受保护18081实时观察，固定旧11资源/三配置/全部连接/entry PID及稳定容器身份；默认prepare不写运行资源。apply前重新比较全部旧pins。
4. 全部前提通过且另记experience-preflight后，独占保全旧adapter字节、fsync新临时文件、比较后os.replace；只向同一原entry PID发送SIGTERM等待supervisor拉起精确新进程，实核新模块来自已装文件和原配置/旧路由/原历史保留。失败保留attempt、阶段和实际已做变更，不自动重试或回滚。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。明确缺件、漂移、资源变更超出adapter或进程歧义均拒绝。
- 是否从根因和长期维护角度解决：是。永久产品新增目录独立绑定，安装使用正式已提交资源和原校验器，保持控制包与UI资源提交区别。
- 是否存在临时补丁或绕过：否。此为任务精确部署入口，不替代用户备份/恢复操作；普通用户无需使用该入口。

## BDD

- Given 缺少真实资源构建/测试或任何旧pin漂移，When prepare/apply，Then 明确失败，不写运行资源或发SIGTERM。
- Given 明确只有adapter变化，When apply，Then 保全原字节、写后核新SHA，其余10资源/三配置/全部原连接及18081保持，只有原entry PID被重载。
- Given 中途失败或不明确终态，When 再次调用，Then 保留失败且禁止盲重试，不生成PASS或改写旧证据。
- Given 新adapter安装但仍是旧配置，When 原配置/原目录查询，Then 原操作执行和查询绑定仍通过；该观察不冒充新三来源/三目标UI验收。

## 经验门禁

- Trigger：Spug适配器目录路由资源正式安装。
- Preflight check：干净已提交精确资源worktree/11pins/实际测试日志，唯一18080容器与绑定目录、受保护18081、原entry和全部配置连接旧pins。
- Blocker：任一缺件/漂移、其它资源变化、进程或实例歧义、未知尝试。
- Verification：真实RED/GREEN，独立资源构建与实际安装/新PID/模块/原配置证据；完整UI另验。
- Forbidden action：不写配置连接/历史，不重启nginx/容器/三服，不触碰18081，不用fixture证明实际安装，不复制未提交资源。
- Evidence：archived-source-catalogue-routing-plan.md、main-program-spug-publication-plan.md及旧install_automatic_spug.py。
