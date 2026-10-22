# 本机 C: Spug 恢复方案

用户明确授权保留原 ZIP，正式适配到 C:。此入口恢复 Spug 本体及其数据库、持久卷、集成页面，不进行全套发布基础设施迁移。

## 路径与边界

- 原始包：`C:/Users/D01021/Documents/Spug-complete-20261022-151627.zip`，不改写。
- SHA-256 验证后展开：`C:/Spug/Spug-complete-20261022-151627`。
- 本机代码与私密配置：`C:/Spug/runtime/ops`、`C:/Spug/runtime/private`。
- Compose：展开目录中的 `compose.transfer.json`，包含秘密，只允许当前 Windows 用户及 SYSTEM 访问，不纳入 Git。
- 项目：`intruoyi-spug-transfer`；五个独立命名卷；MariaDB 无宿主端口；Spug 只绑定 `127.0.0.1:18080`。
- 不迁移用户 `.ssh`，不启动 Windows 执行器、SSH 转发或远程引擎。原发布状态和配置归档完整保留，但不是已完成的跨机执行器接管。
- 启动保持原恢复器关闭 scheduler、隔离旧 Redis 瞬时队列的行为，旧 dump 保留为证据；数据库用户、任务和历史保持原记录。

## 恢复与日常控制

`stage-package.py` 对归档逐文件核 SHA-256 后展开；既有输出拒绝覆盖。`restore_spug.py --package <展开目录> --runtime C:/Spug/runtime` 二次核摘要后恢复。已存在目标目录、同名容器/卷或被占用端口时停止，失败现场保留，不盲目重跑安装。

恢复完成后的启动、检查仍使用原包的 `transfer.py start` 和 `transfer.py check`，以 Python 3.12+ 在展开目录执行。不要再次执行原 `install`，它针对 D:/E: 全套迁移，不适用于本机布局。

```powershell
docker compose -p intruoyi-spug-transfer -f C:/Spug/Spug-complete-20261022-151627/compose.transfer.json stop
docker compose -p intruoyi-spug-transfer -f C:/Spug/Spug-complete-20261022-151627/compose.transfer.json ps
```

禁止使用 `down -v`、删除卷或覆盖旧文件来消除安装冲突。恢复输入为在线采集数据，不能冒充业务服务全量备份或原子切换。

## 验收

镜像 ID 与包内 manifest 一致；五个卷和 C: bind mounts 对应同一项目；scheduler STOPPED；MariaDB 表检查通过；恢复记录与原包一致（3 主机、14 任务、1 用户、157 历史）；真实浏览器登录及发布中心、备份恢复页只读检查。执行器离线状态必须明确显示，不能伪造已接管成功。
