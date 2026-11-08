# 三服恢复目标只读核查结果

> 本文保留“进行补齐”前的调查快照，以下“尚未实现”仅描述该阶段。最新本机实现与测试见task.md、execution-log.md，安装范围见installation-plan.md。远端尚未安装或恢复，.57异常在本轮复查仍未解除。

## 结论

当前 Spug 尚未把 IntRuoyi 主实例接成三服覆盖恢复目标。问题不是备份包列表未读取，也不是操作人员需要先选一种固定目的地。用户按次选择 .57/.58/.59 的需求应保留；基础设施需要一次正式接入，随后每次从页面选择。现有界面已经具有服务器选择及覆盖确认，不应以新建动态登记页面代替缺失的执行配置。

本次仅执行已授权的只读核查；未恢复数据、停止服务、安装执行器、修改服务器配置或修复正式服。功能仍未交付，任务 blocked。

## 已核实事实

| 范围 | 事实 | 对恢复接入的影响 |
| --- | --- | --- |
| localhost:18080 | 实际使用 C:/Spug/runtime 挂载的 transfer 实例；.57 safe/fast 的覆盖映射均为空 | 页面出现“所选来源尚无可用的覆盖恢复目标”有配置依据 |
| .57 safe 执行服务 | control.json 的 restoreConfigurations={}，监听端口登记为 32657 | 只修改前端选项或 Spug 映射仍不能执行恢复 |
| .59 safe 执行服务 | control.json 的 restoreConfigurations={}，监听端口登记为 32659 | 同样缺少恢复 owner 配置，不能从有来源备份配置推导恢复就绪 |
| 测试服 .58 主实例 | 已登记的 frontend/backend/MySQL 均 running；主库 ruoyi-vue-pro，MySQL 8.0.39，log_bin=1；Redis DB=1 | 已找到实际主实例，仍需配置与登记恢复 owner、核完整锁/准入/存储合同，不能宣称可恢复 |
| 审查服 .59 主实例 | 已登记的 frontend/backend/MySQL 均 running；主库 ruoyi-vue-pro，MySQL 8.0.39，log_bin=1；Redis DB=1 | 同上；已登记主前端发布端口为 38081，不凭历史说明改到另一个实例 |
| .58/.59 主存储 | 主实例 MySQL/MinIO/Redis 使用各自 named volume；本次运行容器清单中同卷 RW 挂载仅见相应角色 | 类型与现有替换引擎方向相符；尚未完成全部停止容器引用、volume driver/options、writer、容量和当前恢复点适配证明 |
| 正式服 .57 主存储 | MySQL=/opt/intruoyi/runtime/data/mysql；Redis=/opt/intruoyi/runtime/data/redis；MinIO=/opt/intruoyi/runtime/data/minio，均 bind | 现有 recovery_replace.verify_services 明确要求 Type=volume，当前正式服不能套用已有独立卷替换合同 |
| 正式服运行异常 | docker ps 显示 intruoyi-backend Restarting (137)；主机 load average=1279.80/1275.26/1264.89；32GB 内存中 MemAvailable 约2.9GiB，10GB swap仅余约2.6MiB | 正式服不得标记恢复就绪；后台精确 inspect 超时，没有取得 OOMKilled 证据，不能把 137 直接断言为 OOM 根因 |

## 正式实现与验证范围

1. 复用现有页面：固定备份包及来源，每次选择目的服务器和恢复方式；预检展示真实主实例、库、附件与 Redis 范围，最终确认绑定不可变目标。
2. 将三服资源定义、来源到目标的登记、桥路由和目标执行服务作为同一受控安装单元交付；一次基础登记后不要求用户每次编辑文件。旧任务保留原编号和原目标路由。
3. .58/.59 需要补齐真实主实例恢复配置并验证现有引擎的完整准入合同；不得把历史 fresh 引用复制为 overwrite 引用。
4. .57 需要正式的 bind 存储恢复合同，覆盖精确路径身份、符号链接/挂载漂移、物理目录重叠与其他 writer、NAS排除、共同锁、失败保留和重试边界；先 BDD/TDD，再实现，不能仅放宽 volume 条件。
5. 正式服异常单独处理。当前权限只允许只读检查，不能停止历史实例、重启 backend 或自动修复。恢复就绪验收需等待该环境状态可验证。
6. 本机功能实现可以继续独立设计；当前不能交付可安装的三服完整配置，也不能执行真实覆盖验收。安装/修改远端与实际恢复均须按各自授权范围执行。

## 证据与限制

- read_main_resources.py / main-resources.json：三服资源概要、来源执行配置、数据库/Redis依赖；仅输出非凭据字段。
- read_restore_preconditions.py / restore-preconditions.json：Docker Unix socket 只读 inspect 投影；.58/.59 SQL仅执行 SELECT 元数据。
- inspect_remote.py / remote-inventory.json：运行容器、挂载和网络清单；正式服大范围 inspect 超时，不计为成功。
- inspect_instances.py / registered-instances.json：登记主实例精确查询；正式服超时如实保留。
- SSH 默认密钥首次认证失败；改用本机已有交接 identity 与 known_hosts 后成功，不改服务器认证或 host-key 策略。密钥内容和凭据未进入日志。
- 本次未执行 BDD/TDD、E2E、恢复演练或生产代码变更；只读元数据结果不构成恢复成功或生产修复成功。
