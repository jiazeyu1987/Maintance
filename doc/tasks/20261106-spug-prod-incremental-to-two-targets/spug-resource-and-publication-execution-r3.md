# 完整观察后的显式安装与配置发布

## Goal and current status

in_progress。延续已授权控制组件/目标登记及本地 Spug 更新；当前只读观察 cd869f3b818249b0914e2e9f60bcc254 尚在运行。以下载体已准备但尚未执行；不能将文件存在视为安装完成。

## Milestones and verification

1. 收取同一 r3 观察的真实 terminal、native exit、完整 observationPin；必须 SUCCEEDED/exit0、remoteExitVerified=true、输入不变、门禁已释放。任何未知或失败均拒绝安装，不自动重复观察。
2. apply-spug-resource-delta838-r2.py 仅在上述事实成立后独占生成正式 v2 apply 输入，默认 prepare 通过后调用已提交安装器。安装器自己仍执行完整新鲜前观察及完整后观察，均沿用固定 900 秒停滞/1800 秒硬限，不能跳过旧合同。
3. 三个原文件全部独占保存并 fsync 后，才原子替换 adapter/app.js/simple.js；仅向已核原 entry PID 发送 SIGTERM，核 supervisor 新 PID。其余八资源、三配置、全部连接、任务与历史、18081 均须保持。外层 4200 秒只用于承载两个各自有界的观察及安装，不延长任何单次观察预算。外层等待过期是未知，不是成功或重试依据。
4. 真实三文件安装核心及私密后观察 PASS 后，publish-spug-45r6-after-delta838-r1.py 才组合已核三服原 selector/baseline 与实际 afterObservation.spug，独占生成 v2 publication 输入。正式 prepare 拒绝任一 pin 漂移。
5. 发布器按固定十二阶段先全部 preflight，再 publish、verify；12 selector、33 应用、3 任务、原历史连接和所有旧字节均核对。业务容器、挂载/fstab、控制身份或受保护 Spug 漂移即失败保留。此步骤不派发备份或恢复。每阶段原预算不改；外层等待不赋予自动重试权。
6. 真实完整目录/UI/自动增量与三目标恢复验证仍为独立后续里程碑，发布 PASS 不能替代它们。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。未知进程或单阶段失败保留原件，禁止自动重试/回滚。
- 是否从根因和长期维护角度解决：是。使用固定已提交正式模块与新鲜实际证据，安装与配置发布依赖单向明确。
- 是否存在临时补丁或绕过：否。载体仅固定正式执行输入，不修改产品校验或旧报告。

## 经验门禁

- Trigger：本地 Spug 三资源安装及三服登记配置发布。
- Preflight check：原操作真实终态、固定 de781e7 模块 SHA、c7728ad 干净构建及真实测试、delta838 明确前后 pin、45/r6 四控制原件、唯一18080与受保护18081、原业务/历史/挂载保护。
- Blocker：任何原 pin 漂移、残留观察门禁、未知/重复 attempt、完整前后观察不等或十二阶段不闭合。
- Verification：原始 stdout/stderr/dispatch/terminal、正式核心/私密证据、原旧字节读回、新 entry 精确身份、原生 selector 及产品配置读回。
- Forbidden action：不重启整机/Docker/容器/nginx，不改 NAS/fstab，不改归档或历史成功记录，不派发备份恢复，不删除其它任务工作区/控制台。
- Evidence：正式安装与发布工具的测试/父验证、当前 r3 原观察、独占请求/完成回执及 execution-log.md。实际写入前须另记 GREEN: experience-preflight -> PASS。
