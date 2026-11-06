# 原 MAIN 的语义健康检查与362失败续办

## Current Status
completed

## 事实与目标

History362实际FAILED_RETAINED/exit1，UTC2026-11-06 06:48:54，错误ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED。SQL导入和完整结构/数据回读已完成，原生数据库比较为SCHEMA_DATA_EQUAL_PENDING_APPLICATION_PROOF；对象物理文件步骤已有读回证据，但随后原MinIO启动后的Docker健康声明检查失败，尚未完成对象版本/引用/Redis/业务验收。703份控制/校验证据已固定SHA并复制至私密目录，1170份工作文件共18656671005字节保持原位。原361的205份证据及8个本地原件保持。

原MinIO、backend、frontend的Config.Healthcheck为空；MySQL/Redis已有实际healthy。原MinIO由本次流程于06:48:45启动，backend/frontend仍停止，原MySQL UUID保持、event_scheduler=OFF、事务0。目标和来源合同不得改变；原容器、镜像、应用配置和挂载不得为通过检查而重建或修改。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。登记MAIN采用固定语义健康策略，始终验证HTTP就绪/UP；原有Docker检查存在时额外要求通过。非MAIN继续原严格Docker健康逻辑。连接未就绪仅在明确有界启动窗口内重试，超时/协议错误保留失败原因，不声称成功。
- 是否从根因和长期维护角度解决：是。正式组件封装MAIN角色协议和证据，执行前验证端点/端口/原配置绑定，独立验证真实返回值，随SAFE/FAST实际封包并回归。续办仅在原锁及精确身份/失败/保护证据下停下本次恢复启动的MinIO，追加意图和退出证明。
- 是否存在临时补丁或绕过：否。不得删除健康检查、把running当healthy、伪造Docker Health、放宽隔离演练健康要求、修改原容器声明或旧失败终态。

## BDD

1. Given 登记MAIN三原服务无Docker HEALTHCHECK、原身份/配置/端口保持；When 安全恢复启动原服务；Then MinIO真实就绪200、backend真实JSON status=UP、frontend HTTP200后才记healthy，并固定探测证据。
2. Given 容器身份/配置/端点漂移、HTTP重定向、错误状态或非UP后端；When 健康检查；Then 拒绝或在有界启动窗口后失败，不重复启动、不修改业务。
3. Given 原服务已有Docker健康声明；When HTTP健康但Docker unhealthy/状态缺失；Then 不通过；普通演练目标仍要求原Docker检查。
4. Given 362实际终止、原失败pins/预约/归档与端口保护保持、仅本次启动的原MinIO仍运行；When 显式授权的续办停写；Then 只停该MinIO并追加意图/退出/观察证据，原703/205材料不改，原调度器OFF保持。未知启动来源或运行writer拒绝。
5. Given 正式修复已提交、新专属精确提交构建及安装通过、362正式同点clearance和本地原件保存通过；When 真实Spug再次一次最终请求；Then 新独立操作完整成功，不能把本次已通过数据库阶段冒充新操作成功。

## 里程碑与验证

1. [x] 362原终态及703份原件保全；原健康配置/服务状态只读确认。
2. [x] 实际端口/MinIO只读就绪核对；BDD对应RED。
3. [x] 最小正式实现、GREEN、416项及3子场景回归、真实HTTP/原MinIO只读验证；限定实现提交9dce318。
4. [x] 新专属精确提交构建126文件全部SHA/编译；原703+205材料保持，原MinIO单次精确停写及只读复核追加留证，仅重载本任务控制，195运行保持。
5. [x] 正式同点/同目标保护及调度器custody交接；908远端与16本地失败原件逐字节保持。真实Spug新单次请求History363原生SUCCEEDED/exit0，885表/5916对象版本/引用/Redis/三角色真实语义健康与业务页面、保护释放独立验收PASS，首次原调度器ON已恢复。
6. [x] 五个专属构建副本实体/Git登记均删除，无新提交不需合回；自有测试容器/卷已删除。稳定控制与其它190业务保持，closeout-verification.json于UTC10:13:21 PASS，最终记录限定提交见execution-log。

## 经验门禁

- Trigger：原MAIN无Docker健康声明、物理复制后MinIO启动健康合同失败。
- Preflight check：核实际失败exit/进程终止、703+205证据pins、原容器健康声明/端口/镜像/配置摘要、当前写围栏/归档只读/调度器OFF、MinIO确由本次启动、其它writer停止。
- Blocker：未知身份、未知启动者、活动worker、运行业务writer、保护/证据漂移、端点或协议不受支持，阻止停写/安装/clearance/新派发。
- Verification：真实RED/GREEN/回归、真实HTTP协议检查、实际封包全部SHA、新代安装/原件保持、真实新单次UI请求、完整原生数据和程序验收。
- Forbidden action：不伪造健康、不跳过检查、不改原容器、不删除失败/工作材料、不手工改预约或调度器、不卸载共享NAS、不重复派发。
- Evidence：healthcheck-failure-diagnosis.json、后续测试/构建/精确停写/安装/clearance与独立验收；敏感原件仅任务私密目录。

执行选择：根因修复为正式recovery_main_health组件；续办停写使用本任务明确授权的精确运维脚本quiesce_failed_health_storage.py，复用正式只读观察、原锁/预约及保护验证，不新增通用自动停服务能力。启动来源纯门禁5项实际测试通过，覆盖错误操作/命令/未知或失败退出、重复启动、重启时间及不稳定状态。正式组件17项及3个子场景通过，真实原MinIO无代理探测及三角色原配置/端口绑定PASS。
