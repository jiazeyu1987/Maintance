# 准备空恢复环境

在 `/backup-restore/` 选择应用、备份点和备份服务器 `172.30.30.59`，点击“准备空恢复环境”，核对清理范围后确认一次。后台顺序执行准备最小依赖、清理旧环境、初始化空目标；随后用原恢复入口验证并登记新目标，显示 `READY`。此按钮不开始恢复，用户继续使用原“开始恢复”按钮。

只支持固定 `.59`。原地覆盖目标及其历史保留为原登记记录；新空目标每次使用新引用。失败立即停止并保留记录，不自动重试或回滚；连接结果未知时查询原任务，不能另起一次清理。恢复或准备正在使用同一目标时拒绝并行准备。

## 安装

1. 将同一版本的 `ops/spug/` 完整安装到 Spug 的 `/opt/intruoyi-spug`；现有 Compose 整目录挂载会带上三个 `prepare_target*.py` 和 `smallapp-ui/prepare-target.{js,css}`。更新 `smallapp-entry.locations.conf` 后按原安装方式校验并重载 Nginx，只重启本入口进程。代码挂载保持只读。
2. 本功能需要在私密目录创建新目标路由并更新桥接配置，`compose.yaml` 中 `/run/intruoyi-spug` 改为可写配置挂载。私密目录只允许管理员和入口后台访问，目录权限 `0700`、文件 `0600`；控制认证文件内容不变。已有容器须在实际部署时应用挂载变更，本地代码修改不会重建运行容器。
3. 在 `.59` 数据盘的独立 `toolRoot` 先安装 Python、`prepare_target_native.py` 及原恢复引擎完整依赖。安装位置必须在清理范围外；不能继续从计划删除的旧 `backup-restore-lab` 运行 Python。`stateRoot` 保存本功能记录和独立恢复控制服务配置，也必须在清理范围外。NAS 挂载和 Docker 数据根目录均保留。
4. 根据已核实的 `.59` 机器、旧资源和所选备份填写 native 私密配置，再将其和程序的真实字节数/SHA 填入 Spug 配置。禁止提交私密文件、凭据或镜像归档。未安装配置时界面显示“准备功能未配置”。
5. 新控制服务固定为 `spug-prepare59-restore.service`，监听 `.59` 的指定专用端口，复用既有控制认证。该端口必须能从 Spug 容器访问；它与旧控制入口分别运行。准备完成时，后台用原 `HttpBridge` 和恢复选择准入验证新控制器，再更新 entry、bridge、simple 三份配置。

本地开发验证不执行上述服务器安装、停服、清理或恢复。`.59` 是否实际 READY 以已安装版本的任务记录及真实选择结果为准。

## Spug 私密配置

文件固定为 `/var/lib/intruoyi-spug/prepare-target.private.json`。下列是结构示例，尖括号内容必须替换为真实值，不能原样启用：

```json
{
  "schemaVersion": "SpugPrepareTarget/v1",
  "host": "172.30.30.59",
  "applicationId": "<已登记应用>",
  "sourceConfigRef": "<对应来源>",
  "stateRoot": "/var/lib/intruoyi-spug/prepare-target-operations",
  "pythonPath": "/mnt/intruoyi-data/recovery-tools/python/bin/python3.12",
  "nativeProgramPin": {"path": "/mnt/intruoyi-data/recovery-tools/prepare_target_native.py", "bytes": 1, "sha256": "<64位真实摘要>"},
  "nativeConfigurationPin": {"path": "/mnt/intruoyi-data/recovery-tools/prepare-target.private.json", "bytes": 1, "sha256": "<64位真实摘要>"},
  "sshTransport": {"host": "host.docker.internal", "port": 18559},
  "publication": {
    "entrySettings": "/var/lib/intruoyi-spug/smallapp-entry-settings.json",
    "bridgeSettings": "/run/intruoyi-spug/smallapp-bridge.private.json",
    "simpleSettings": "/var/lib/intruoyi-spug/smallapp-simple-settings.json",
    "credentialRef": "<现有控制认证文件名>.json",
    "sshTransport": {"host": "host.docker.internal", "port": 18559}
  }
}
```

`sshTransport` 只用于已有 `.59` SSH 转发；直连 Spug 已登记 `.59` 主机时省略外层字段。登记后的遥测使用既有 `18559` 转发。浏览器只能提交应用、备份点、操作编号和预览摘要，不能指定路径、主机、命令或凭据。

## Native 私密配置

配置值来自实际机器、现有 owner/control/registration 文件、Docker inspect 和所选 NAS 备份；不从旧电脑目录猜测。现有 MAIN owner 可作模板，生成器仅保留该来源和应用/数据配方，移除旧 MAIN/replacement 及目标历史策略，再写入新资源身份。

| 字段 | 必须填写的内容 |
| --- | --- |
| `host`, `machineId`, `dockerEngineId` | 固定 `.59`、实际 machine-id 和 Docker ID |
| `dockerPath`, `dockerRoot`, `dataRoot` | Docker 程序、实际数据根（当前为 `/mnt/intruoyi-data/docker-engine`）、本地数据盘 |
| `toolRoot`, `stateRoot`, `formalModuleDirectory` | 保留的完整 Python/引擎/正式数据模块及私密操作记录目录 |
| `hostReservationRoot`, `sourceLockPaths` | 固定 `/var/lib/spug-restore-resources`；需要协作的现有来源锁路径数组 |
| `archiveRoots` | 已挂载且必须保留的 NAS 根目录数组 |
| `cleanup` | 明确的 `directories`、完整 `containerIds`、`volumeNames`、完整 `networkIds`、`serviceNames` 数组，无通配符 |
| `dependencies` | `{source,destination,mode?,uid?,gid?,rewriteJson?}` 数组；destination 相对 toolRoot；需改写引用的 JSON 按叶子到引用者排序 |
| `ownerTemplatePath`, `ownerTemplateTargetRef` | 当前真实 `RecoveryMinimalConfiguration/v1` 及其中目标引用 |
| `targetPrefix`, `subnet`, `templateSubnet`, `frontendPort` | 新目标名前缀、独立 IPv4 网段、旧模板网段和仅 loopback 暴露的前端端口 |
| `database`, `mysqlCaseRule`, `mysqlClientFile`, `redisSecret` | 数据库名、大小写规则、容器内 MySQL 凭据文件位置、工具目录相对 Redis 凭据文件 |
| `templateDataPaths` | 旧 mysql/minio/redis 宿主路径映射，生成新目标时替换 |
| `resourceBudget` | 现有引擎的 `RestoreResourceBudget/v1`，使用实际内存及覆盖新数据/工具/状态目录的磁盘预算 |
| `points` | 恢复点引用映射到 `{applicationId,sourceConfigRef,imageArchivePin,roleImages}`；roleImages 为五个角色的实际镜像 ID |
| `services` | mysql/minio/redis/backend/frontend 五个角色的实际启动配置，见下方结构 |
| `control` | `{templatePath,registrationPath,serviceName,engineDirectory,pythonPath,listenAddress,listenPort}`；模板为现有 `SmallAppExecutionServiceConfig/v2` 和 `ApplicationRegistration/v1`；serviceName 固定，listenAddress 固定 `.59` |

服务结构示例（各镜像的 UID/GID、环境和命令必须来自实际配置）：

```json
{
  "role": "mysql", "memoryBytes": 4294967296,
  "templateIp": "172.28.140.32", "dataDestination": "/var/lib/mysql",
  "dataOwnership": [999, 999], "environment": ["MYSQL_DATABASE=ruoyi-vue-pro"],
  "binds": [{"source": "private/mysql-client.cnf", "destination": "/run/recovery/mysql-client.cnf"}],
  "command": ["--lower_case_table_names=1"]
}
```

可选服务字段为 `user`、`workingDirectory`、`entrypoint`、`healthCommand`。需要替换地址的只读配置 bind 设置 `rewriteAddresses:true`，副本写入本次目标的 config 目录。认证文件内容不进入页面。

最小依赖阶段加载所选备份的镜像，收拢当前凭据、应用配置及被清理目录中的来源/control/catalogue JSON。保留模板和改写后的真实 pins 到 `toolRoot/prepared-inputs`，再次准备直接使用这些固定副本。NAS 归档本体不复制、不改写。已有 control 的认证、程序 pins、来源和归档目录必须全部指向保留文件。

新目标使用 `dataRoot/<newRef>/{mysql,minio,redis}` 直接 bind。仅启动 MySQL/Redis 并验证为空；MinIO、前后端保持停止，MinIO 目录物理为空。后续再次准备只加入本功能上一轮记录的精确容器、网络及目录清单；明确已不存在的旧资源视为已清理，Docker 本身失败仍中止。

## 接口与记录

原 Spug 登录、查看/执行权限及 Origin 规则继续适用。

| 接口 | 用途 |
| --- | --- |
| `GET /prepare-target/config` | 是否配置、固定主机和明确错误 |
| `POST /prepare-target/preview` | 一次读取备份点及清理/保留范围，返回摘要 |
| `POST /prepare-target/operations` | 确认后持久预留并返回 `202`；重复编号返回原记录 |
| `GET /prepare-target/operations/<operationId>` | 三阶段进度、成功/失败/未知状态 |
| `GET /prepare-target/history` | 读取持久准备历史 |

预览后台预算最多 75 秒、代理 80 秒、页面 85 秒。实际准备异步运行，普通提交预算不变；提交不重复执行预览或整链查询。初始化本身只返回 `INITIALIZED`；本地登记和真实恢复选择准入通过后才发布 `READY`。
