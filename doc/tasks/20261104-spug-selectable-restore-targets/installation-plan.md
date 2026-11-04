# Spug 三服主实例恢复安装与验收计划

## 当前执行结论（2026-11-04）
用户已明确授权安装控制组件、登记配置和本地 Spug 更新，不执行恢复；同时确认所列 EDHR MinIO 账号仅供 IntRuoyi 主程序使用。

- .58/.59 的主实例合同、实际存储/配置pin、writer证据与共同锁已经核验，控制服务active，认证准入通过，本地Spug已登记为可选覆盖目标。
- .57 仅stage安全程序组件；最新精确backend inspect仍4秒超时、load约1553，未生成可执行目标，不启用、不修复或重启业务程序。
- 三服各121程序文件SHA一致。真实页面已登录、选择两服、打开绑定目标的确认并取消；恢复操作和claim均0，业务容器启动时间未变化。未验收真实数据恢复。
- 独立来源/两目标SSH通道已迁入稳定目录，有互斥、自动重连及当前用户登录计划任务；未重启机器验证启动项。实现已合入int_main并在合并结果验证，两个临时发布checkout已移除。
- 最终结果见task.md及installation-status.json、browser-choice.json、implementation-integration.json、release-worktree-cleanup.json。原需求的正式目标部分仍blocked，开发worktree保留。

以下为安装前设计，不代表尚待取得安装授权；历史失败和修正见execution-log.md。

## 可审查安装范围
1. 将本次已提交目标构建的安全执行包放入任务专属安装目录，核对包清单和每个程序 pin；不使用lightweight承接主实例覆盖。
2. 为 .57/.58/.59 各生成一个私密主实例 target v2，读取现有 Docker、数据库 UUID、配置文件 pin、mountinfo 和共享消费者。安装控制配置与登记选择器；若使用新控制实例，先证明端口/目录未占用，配置同来源应用ID及安全引擎引用。
3. 来源程序、现有备份链、原编号及历史执行器路由保留；目标执行器必须能按原绝对路径读取源范围、身份及NAS归档。只读挂载或现存文件须逐 pin 核对，禁止修改归档字节或改写清单路径来“适配”。
4. 更新localhost:18080的simple/entry/bridge映射及任务涉及的adapter代码；保留当前运行UI和其他任务改动，不覆盖整套ops/spug目录。
5. 仅在所有准入通过后重载本任务的恢复控制服务和本地入口。此安装范围不包含主程序、MySQL、MinIO、Redis的停止或重启，不包含任何数据恢复、清理历史容器或NAS修改。

实际恢复依旧由用户在Spug里选择包、选择目标、查看覆盖确认并提交。安装检查及页面验收均止于选择/核验/取消，不点击最终恢复确认。

## 三服当前事实与安装前必查

| 地址 | 目标 | 已知事实 | 上线前准入 |
| --- | --- | --- | --- |
| 172.30.30.57 | 正式主实例 | MySQL/Redis/MinIO为bind；后端此前Restarting(137)，本轮load约1376且inspect超时 | 先恢复可读取且稳定的身份/运行态；本安装不自行修复或重启。必须证明MinIO物理根、业务库和Redis库的写入者独占归属 |
| 172.30.30.58 | 测试主实例 | backend/frontend healthy；数据服务为local named volume；库ruoyi-vue-pro、Redis DB1 | 取得完整只读实例合同、配置pin、所有容器RW消费者与资源归属证据 |
| 172.30.30.59 | 备份主实例 | backend/frontend healthy；local named volume；页面实际入口:38081 | 同上；使用已核实Python路径和真实端口，不套用过时8081 |

三服均已存在来源canonical身份/范围文件；本轮只核存在，不将其当字节一致性证明。还需源目录 `/selections` 认证连通、完整归档访问、完整祖先链和所有 pin 核对。

不得把 `writerAdmission.exclusiveResources=true` 当人为豁免：必须核数据库连接/应用依赖、对象存储用户与实际物理范围、Redis数据库消费者，并将可审查证明保存为私密pin。无法证明则该目标不得登记为可执行。正式服MinIO容器名带ragflow，不据此推定归属，也不允许清理其他应用资源。

同一主实例的备份与覆盖恢复必须使用共同锁；跨来源恢复到某一目标也必须与目标自身备份使用同一目标资源锁。锁、状态及操作目录均不得位于业务数据或NAS。异常/失败操作的保留状态不得删除来解锁。

## 配置生成接口
`ops/spug/restore_target_registration.py --input <private-inputs.json> --output <new-private-plan.json>`

输入 `SpugMainRestoreRegistrationInputs/v1` 包含当前三份Spug设置、来源registration及三个明确target。每个target须提供服务端owner配置、服务端control配置、standard variant、私密配置根、bridge文件/内容、progress路由和预检证据pin。程序只生成 `PLAN_ONLY`，附当前设置与control的canonical SHA256，绝不连接服务器或安装。

目标的主实例合同由 `recovery_main_target.capture_main_application` 从显式Docker inspect/network观察与真实证据生成；存储合同由 `recovery_replacement_storage.snapshot_mounts` 生成。它们不造资源、不填默认成功状态。

owner的source增加：
```json
{
  "archiveCatalogue": {
    "schemaVersion": "RecoveryArchiveCatalogue/v1",
    "maximumPointFiles": 10000,
    "maximumMetadataBytes": 67108864,
    "sourceAdmissionPin": {"path": "<private access config>", "bytes": 0, "sha256": "<actual digest>"}
  }
}
```
此为字段说明，不可安装的示意值。access文档版本 `SmallAppSourceCatalogueAccess/v1`，字段为 `selectionUrl/authCredentialRef/applicationId/engineSelectionRef`；凭据只引用受保护文件，不写入Git、浏览器或日志。

每次恢复时保持原七字段请求不变，按指定operationId自动生成不可变owner配置：读取来源当前有效恢复点、在已登记归档中找到相同backupId、验证全部祖先及原始发布证据，再交安全引擎完整核验。后续新备份无需逐次人工复制point selector或编辑恢复配置；程序版本不兼容仍须明确拒绝。

## 安装和回滚门禁
- 安装前记录experience-preflight PASS、包SHA、目标提交、当前配置SHA、服务单元与进程归属；写入前重新比较当前SHA，漂移则停止。
- 先写新私密文件，逐字节读回与pin校验，最后用既有registration selector的expected_pin比较发布，不覆盖不明新版本。备份原配置与服务定义，不保存凭据明文到可提交日志。
- 首次仅启动自有控制实例并核认证 `/selections`；来源普通目录不依赖无关目标，所选目标通过 `/selections?targetConfigRef=<ref>` 做真实观察。
- 本地Spug选择.58/.59/.57，检查包/源/目标/覆盖确认绑定；取消后无恢复操作产生。新恢复点自动发现、旧历史保持原route；真实恢复须另行授权及独立测试环境验收。
- 任一主实例异常、共享存储归属不明、source pin变化、程序版本不兼容或私密凭据/服务访问缺失，停止对应目标安装。不改成快速模式，不移除检查。
- 未受理恢复前可恢复原Spug映射、登记选择器、控制服务配置；已经受理恢复时先按原operation查询，不重试或改路由。安装回滚不得删除失败恢复保留、业务目录、历史容器或NAS。

## 当前仍需完成
仅正式服稳定运行身份及后续完整资源合同仍未通过；.58/.59合同、writer证据、安装及页面选择/取消已完成。正式服不通过前不得宣称三服全部可选。实际恢复不在本轮授权范围。
