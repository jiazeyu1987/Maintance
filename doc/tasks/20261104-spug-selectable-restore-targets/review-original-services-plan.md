# 审查服 .59 原实例恢复可用计划（待单独授权）

此计划尚未执行业务启动或归档挂载。现有明确授权覆盖三服控制组件及登记；后续重启后原业务恢复授权只列.57/.58，未包括.59。本计划只补.59原实例运行和原归档路径，不执行任何数据包恢复。

## 只读前提已经确认
- 主机172.30.30.59，现有原目标intruoyi-main-59-safe-restore-20261104-v1；入口172.30.30.59:38081。frontend原容器运行，另外四原容器停止；restartPolicy=no，不以启动其它实例代替。
- 三原数据目录及host bind的device/inode、backing完整mountIdentity均保持，已有数据仍在；只变更重启后的mountId，已发布独立登记回执。无operation、claim或宿主活动恢复预约。
- 新安全控制122文件摘要通过，正式dataLimits16GiB/SQL展开64GiB；控制服务active/enabled，不依赖临时worktree。
- /mnt/intruoyi-backup-nas当前已挂载//172.30.30.4/IT共享，完整新FULL的point.json SHA为af95ffa94e9478bd32935c6e0c662aa5590854a0cda7597b84a25abd81a8f128。原canonical根/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas存在且为空，当前未挂载，不能复制包或改清单路径来替代。

## 准备执行的精确范围
1. 执行前重新核主机/boot、所有配置pins、原目标共同锁、数据设备/inode/backing、原容器ID/镜像/挂载/网络、无活动恢复及无并行维护。核任一漂移立即停止，不创建替代实例或空库。
2. 仅将现存/mnt/intruoyi-backup-nas以bind,ro挂到上述空canonical根，新增本任务专属systemd.mount及恢复控制的RequiresMountsFor依赖；不删除/清空/移除/mount覆盖原NAS，不修改共享数据或fstab。读回必须仍是同一CIFS共享且readonly，新FULL point.json SHA一致。
3. 仅启动以下原有、目前停止的四个容器，不重建、不改镜像/Env/挂载/网络/restartPolicy；先原mysql/redis/minio，身份和健康只读验证后才启动backend。保留已运行frontend和其它业务。

| 角色 | 精确原容器ID | 名称 |
| --- | --- | --- |
| mysql | 4376cb8d12c95ec485589b2fc8edabed3d9c631fcd52f715c4b2800f1b4cde8e | intruoyi-prod-nas-restore59-20261020-native-mysql |
| redis | 99d136c09a948643f5f4bb7ff6fb1f0402cd856dc5aeebe91e5baf289dbd3e48 | intruoyi-prod-nas-restore59-20261020-native-redis |
| minio | eb40cfe31e8046cf281c33d1a9b7cc50a2ecd30cb2b5a51d4248dce5f20b38d7 | intruoyi-prod-nas-restore59-20261020-native-minio |
| backend | 285244884c5e056ce1e37d073a9356c9dd34e9d97dc8ea3af07183b9929c79d8 | intruoyi-prod-nas-restore59-20261020-backend |

4. 核原数据库UUID、后端UP、frontend38081 HTTP200、版本/真实登录只读页面。认证selected-target准入及真实Spug选择确认后返回必须通过；零恢复POST、零业务数据测试写入。不通过保留原错误和证据，不手工改表、回填、导入或切目标。
5. 不重启整机、Docker或无关服务，不停止其它业务，不创建/删除容器，不恢复数据包。若某原服务无法启动，停止对应后续步骤并给出实际原因；不擅自扩至端口强杀、迁移或重建。

## 预期交付与限制
通过后仅证明.59原实例运行、归档可读和目标准入可用，不冒充在.59完成真实数据恢复。正式服.57的目的地支持仍需单独完成现有可写运行挂载/对外数据端口的正式合同与资源writer核验；不能直接解除禁用。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；恢复原有运行前提与canonical只读路径，保留严格身份及资源校验。
- 是否存在临时补丁或绕过：否；不重建替代实例，不改原数据，不跳过准入。
