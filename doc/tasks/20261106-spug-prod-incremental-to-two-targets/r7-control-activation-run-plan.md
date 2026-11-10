# r7 四控制激活与原 Spug 配置验收

## Current Status

prepared_not_dispatched。用户此前已授权三服控制组件安装及本地 Spug 更新；本步骤沿用该范围。b5fa4c5 双包已由本次专用干净 worktree 构建并完成 273 项真实 Linux 验证，三服 r7 暂存已通过。当前仅准备有限执行载体；不执行业务恢复。

## 目标、里程碑与预期验证

1. 完成新只读验收 helper 的本机合同，确认原七配置、四旧连接和 27 项登记与新代次相容。实际已完成 r7 generation 是激活后的验收输入，不能循环要求它先于激活存在。
2. 按既有正式 ORDER 顺序逐次执行：59 target、58 target、57 target、57 source。每次先正式 prepare，再显式 activate；后一步须绑定前面实际核心报告。任一步失败或终态未知立即停止，保留原件，不自动重试。
3. 每次由正式 activation 程序核原进程、业务容器、完整历史、物理锁、epoch、原挂载及 fstab，独占追加本任务 drop-in，仅重载选定控制服务，再核真实新 PID/argv/env/引擎/配置/API/来源策略。原组件与原配置保留。来源最后一步必须证明旧错误 READY 转为原 24 小时策略要求的准确 AGE_EXPIRED/BASELINE_REQUIRED，或原正式合同许可的未过期 READY。
4. 四份实际 core/rich 全部成功后，以唯一 generation inspector 验证完整证据，独占写新 generation，再用正式 loader 重读。不得用暂存报告或构造成功数据代替。
5. 新鲜只读观察及原六阶段验收通过后，才发布相应独立安装选择；原已发布七配置和四旧连接保持，不把四新名连接文件称作已发布。
6. Playwright 真实登录 Spug，明确要求新 FULL 时从页面提交一次；原编号成功并证实来源恢复后，才从页面提交新增量，核 root/parent/实际包大小。覆盖恢复继续等待目标自动保留、完整读回和首 clear 前门禁。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；失败、超时或缺证据保持阻断。
- 是否从根因和长期维护角度解决：是；使用既有正式安装、策略和 generation 合同，区分控制升级与已发布配置身份。
- 是否存在临时补丁或绕过：否；有限载体不修改生产执行器、不重写旧报告、不重复发布原配置。

## 经验门禁

- Trigger：已授权的三服控制组件升级及真实备份验收。
- Preflight check：固定提交 b5fa4c5、实际包/覆盖/暂存 pins、正式 helper 已提交字节、原 Spug 历史完整托管、本机验收合同、实际前序报告、原服务和数据保持。
- Blocker：任一原件漂移、前序缺失、活动 worker、锁或历史变化、原业务状态变化、远端失败或未知结果。
- Verification：正式 prepare 与 project_core、实际原始 stdin/stdout/stderr/exit 私密保全、generation inspect/load、新鲜六阶段验收和 Playwright 同操作号终态。
- Forbidden action：不重启整机或 Docker、不停主程序、不操作共享 NAS/fstab/18081、不恢复数据、不改 24 小时策略、不重发 376、不以文件暂存冒充运行生效。
- Evidence：chain-policy-verification-b5fa4c5-20261110-r1.json、spug-historical-read-parent-20261110-r1.json、control-generation-scope-parent-20261110-r1.json、三服 r7 原暂存以及后续实际 activation 原件。

执行前须在 execution-log.md 追加 `GREEN: experience-preflight -> PASS`，注明本步范围和原件。有限载体默认只 prepare；只在明确 `--activate` 时派发一次。私密输出不提交。工作树已有其它并行改动，禁止广泛暂存或清理。
