# 空目标实际服务就绪检查

## Current Status
ready_for_closeout

## 目标、里程碑与预期验证
真实 FULL 在数据库及附件复制后报 ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED，FAILED_RETAINED 且有写入。定位实际生成 STANDARD 健康合同与容器健康声明，复用服务真实就绪探测完成 prepared 最小修复；非 prepared 保持原行为。只读确认准备按钮能否处理已终止的写入失败保留状态，缺口上报父任务，不自行清锁。

## 经验门禁
- 上一步 SQL 回读修复已提交 31a670f 交父任务融合，本轮为同一恢复验收后继故障，不覆盖其证据。
- 按 server-access/release-backup-restore 已确认仅 .59，允许本次只读小字段检查；禁止修改远端、重启、清锁或安装。
- 不能将 Docker running 当作业务就绪；既有端点探测必须实际成功，保留超时与失败。
- 复用既有正式生成入口，不引入新组件、通用验证平台或旧历史兼容。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；prepared 使用明确的服务就绪合同，不吞异常或伪造健康。
- 是否从根因和长期维护角度解决：是；镜像未声明 Docker HEALTHCHECK 与实际服务可用性分开，复用现有探测。
- 是否存在临时补丁或绕过：否。

## BDD 与验证
- Given 准备目标镜像无 Docker HEALTHCHECK，When 实际服务端点返回可用，Then 健康等待成功；端点未就绪、请求失败或身份变化仍失败。
- Given 非 prepared 目标，When 缺少原合同要求的 Healthcheck，Then 原规则保持。
- 先对实际构建输出完成 RED，再最小实现和定向 GREEN/必要回归；不将单元测试称为远端恢复验收。

## 实际证据与实现
- .59 当前 5 容器都未声明 Docker Healthcheck；MinIO 正在运行，但 STANDARD `wait_healthy` 无条件要求 `State.Health`，在附件复制后首先触发失败。后端和前端尚未启动。私密字段证据 `v13-health-fields.private.json` 未输出环境值。
- 实际调用仅 MinIO 及 application.startOrder 的 backend/frontend；MySQL/Redis 继续使用准备阶段已有实际 SQL/Redis 检查，不新增五角色统一探测。
- prepared 分支复用包内已有 `recovery_main_health.probe`：MinIO GET /minio/health/ready、backend GET /actuator/health 且 status UP、frontend GET /。保留目标 bound、精确容器/镜像、运行状态、已声明 Docker 健康状态、有限等待；非 prepared 原方法保持。
- 对失败任务已启动的实际 MinIO `172.29.238.33:9000` 只读执行同一 probe -> ready=true、HTTP 200；使用当前控制配置已有 PYTHONPATH，未安装组件。证据 `v13-health-live-probe.private.json`。
- 实际 native 挂载 nginx 的 backend proxy_pass 为 `172.29.238.35:48081`，frontend listen 80；backend 镜像 EXPOSE 48081 且已查小配置/参数未覆盖 server.port。该端口是当前生成合同，尚不声称后端已实际监听；之后启动仍必须 probe 成功。证据 `v13-health-ports.private.json`、`v13-backend-port.private.json`、`v13-nginx-upstream.private.json`。
- native 子 agent 同步修复精确失败目标重置，见本目录 reset-note.md；共享 host lock 内只解除本工具当前目标已确认终止的失败预约，依赖准备失败仍保留 active，旧恢复证据不改。

## TDD 与回归
- RED: 实际 STANDARD 生成方法 + 真实本地 HTTP 服务，`python -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_prepared_service_health.py` -> 4 failed，均因 ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED。
- GREEN: 同命令 -> 4 passed；添加实际 native.fresh_target 输出到已核端口的窄合同用例，共 5 例。DOWN/503 无成功，已声明 unhealthy 拒绝，身份改变拒绝，非 prepared 旧检查保留。
- REGRESSION: 使用现成 Docker python:3.12-bookworm 和本机既有依赖，`python -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_prepared_service_health.py scripts/tests/test_prepared_database_readback.py scripts/tests/test_backup_target_mounts.py` -> 15 passed。
- REGRESSION: 本机 Python `-X utf8 -m unittest ops.spug.test_prepare_target_native` -> 28 passed，含同一已完成准备操作重复查询无新依赖/清理/释放副作用。
- 本轮对前一提交构建输出差异仅 `common/recovery_minimal_runtime.py`，SHA256 `1f2fc21162e2a6007ea5b641c5776ca954d494a20fdc62ef2919e868b025c895`；加未部署 v12，下一载体只需 data/runtime/native/package。`git diff --check` PASS。
- 未进行任何远端写入、清锁、停启或恢复。工作区仍为父任务 integration-worktree；本地实现与必要验证完成，交父审核、融合及安装，最终远端完整恢复验收未完成。
