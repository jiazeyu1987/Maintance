# 原 MAIN 前端健康端点合同修复

## Current Status
in_progress

## 目标与事实
369 已实际 FAILED_RETAINED/exit1/MAIN_HEALTH_ENDPOINT_INVALID。六条原生指令全部 mutation=false，未产生 replacement-intent 或数据库导入；资源预约通过正式 no-mutation 路径释放。368 clearance 已消费到 369，不能重复消费或删除记录。58 原 MySQL/Redis 继续运行，其余三服务保持停止；59 未执行恢复。

两服原 frontend 登记 ip=127.0.0.1：58 NetworkMode=host，无发布映射，具有已固定只读 nginx 配置；59 bridge，具有已登记固定内网地址及 80/tcp 发布映射。新语义健康组件错误地只接受 MinIO 回环地址。原容器、登记目标与历史配置均不得修改以迁就检查。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。按已固定 MAIN 配置识别既有前端网络模式；证据不完整、端口/挂载/身份漂移或地址不唯一立即拒绝。
- 是否从根因和长期维护角度解决：是。明确前端实际监听地址合同，预检与启动验收共用解析，保留 HTTP200、禁重定向/代理、响应与等待上限；后端 UP 和其它角色约束不变。
- 是否存在临时补丁或绕过：否。不硬编码服务器 IP/任务路径/端口，不放开任意 loopback，不改历史 targets 摘要。

## BDD 与里程碑
- Given 完整固定原 MAIN 前端且登记为回环；When 为 host 网络；Then 由 owner 层显式 frontendReadiness 配置选择真实前端 HTTP listen，绑定原 containerId、完整 serviceConfigurationDigest、原 nginx 文件 pin 和只读挂载，验证配置中精确静态 listen；不得猜端口。实际 58 配置含 8081/28081 前端和 48081 后端代理，选择经原业务验收的 8081。此附加配置在 owner 层，历史 targets 保持原字节；恢复运行时 dataRoot 的合法转换不改变原前端身份绑定。
- Given bridge 前端且登记回环；When 有唯一登记固定 IPv4 附加网络；Then 绑定该固定内网地址与已声明 80/tcp，核网络身份，避免把错误回环当作目标。
- Given 配置/镜像/挂载/网络漂移、未知模式、监听不明确、未固定文件或其它角色非法 loopback；When 解析；Then 明确失败，不能运行恢复。
- Given 369 在写前失败并已消费 368；When 正式续办；Then 按既有 BEFORE_MUTATION/v2 流程签发同点同目标证明，保留两次失败及原件，再真实 UI 单次新恢复。

只读检查还发现既有 BEFORE_MUTATION authorize 固定要求五服务全运行，不适用于从已核销失败继承停写的 369。后续修复需以本次消费关系和上次已固定 observation 证明继承状态，明确校验原保护仍保持，不能为了签发证明启动未验收 writer。
1. [x] 实际两服只读诊断及原生无写证据。
2. [x] 失败测试 RED、最小修复、GREEN、受影响回归与两服真实只读端点核验。
3. [x] 限定实现提交，精确新专属 worktree 构建、仅控制组件升级，旧代次及所有失败原件保留。
4. [ ] 369 正式无写续办，新鲜准入，单次真实 UI 恢复 58 后完整验收，再 59。

## 经验门禁
Trigger：原 MAIN 非默认前端网络及失败续办。Preflight check：真实原配置、挂载 pin、监听/固定网络、无活动 worker、原生 exit 和 mutation=false、原失败 pins、已消费链。Blocker：任一身份不明或证据漂移。Verification：RED/GREEN/REGRESSION、真实两服只读合同、完整恢复原生及业务验收。Forbidden action：改历史、删锁、启动 writer 取证、跳健康、重复提交。Evidence：main-health-endpoint-58.json、main-health-endpoint-59.json、369 原失败和 execution-log.md。
