# 空目标准备：显式本地卷挂载清理

## Current Status
ready_for_closeout

## 目标与范围
真实任务 prepare-8ae30807-c31d-4682-b245-a1d5ac2291e7 在清理第 29 个旧卷时失败；已有 201 个容器和 28 个卷被删除，worker 已终止。父任务确认 3 个明确待清卷的 _data 是来自本机数据盘的 OS bind，fstab 无对应项。本子任务仅增加明确 target/source 的本地挂载清理，以及失败动作、对象、退出码的安全诊断。无远端操作，无自动重试、续跑或旧业务兼容。

## 里程碑与预期验证
1. BDD / RED：明确本地 bind 在删卷前普通卸载；不匹配来源或 NAS 拒绝；已不存在挂载可按原流程清理。
2. GREEN：最小实现配置合同和失败诊断，不改变清理资源清单。
3. REGRESSION：原生执行器及受影响后台测试，精确提交后交父任务审查安装。

## 经验门禁
- 沿用当前真实闭环任务门禁；前一 prepare-admission 子任务已验证提交并交父任务集成，远端执行与最终收口由父任务负责。
- 只修改 integration-worktree 已提交基线，不覆盖并发改动；凭据、私密配置和原始命令不得提交。
- 明确清理卷才允许卸载；来源必须是本地数据盘，不能触及 NAS、工具或运行状态目录；只用普通 umount，不用 force/lazy。
- 本子任务仅本地单元及合同验证，不把单元结果写成远端准备成功。共享命令日志由父任务收口统一记录。
- Windows 中文文件显式 UTF-8；行为改动先 BDD / RED，再 GREEN 和定向回归。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；卸载或删卷失败明确停止。
- 是否从根因和长期维护角度解决：是；Docker 无法删除被外部 OS bind 占用的卷，显式声明并清除本次授权范围内的本地挂载。
- 是否存在临时补丁或绕过：否；不修改历史状态、不强制卸载、不扩展清理范围。

## BDD 与执行证据
- BDD: 本地卷 bind -> Given 三个待清卷有显式本地 source/target，When 准备空目标，Then 先核对实际挂载并普通卸载，再删除原明确卷，NAS 不变。
- BDD: 清理失败 -> Given 卸载或 Docker 命令失败，When 阶段结束，Then 记录安全动作/对象/退出码并返回 FAILED，不输出环境秘密或原始 argv。
- BDD: 失败后新任务 -> Given 上轮已停止且部分卷/挂载已不存在，When 用户创建新准备任务，Then 缺失资源视为已清理，仍保留实际互斥并执行同一授权范围。
- RED: Python `-m unittest test_prepare_target_native test_prepare_target -q` -> FAIL，33 项中 3 个断言失败、3 个错误；旧实现未卸载 bind，未拒绝来源不符或网络挂载，命令错误与公开记录无诊断字段。
- RED: Node `--test-name-pattern='command failure displays'` -> FAIL，页面只显示通用错误码，未显示动作及对象。
- GREEN: 最小实现后 Python 36/36、JS 92/92；后续补充卸载失败停止并持久保存诊断的定向回归。
- REGRESSION: Python `-m unittest test_prepare_target_native test_prepare_target test_prepare_target_http -q` -> PASS 37/37；Node `--test ops/spug/smallapp-ui/prepare-target.test.cjs ops/spug/smallapp_ui_safety.test.cjs ops/spug/smallapp_restore_result.test.cjs` -> PASS 92/92；`git diff --check` -> PASS。
- 真实证据合同：安装 agent 使用已有 inventory59.private.json 确认源挂载 `/mnt/intruoyi-data` 为 ext4、设备 253:3、源 `/dev/mapper/cl-home`、root `/`；3 个 bind 的设备/文件系统/root 与显式 source 一致，Docker Mountpoint 与 target 相同。本子任务未访问或修改远端。
- 发布边界：只改 native、后台诊断传递及已有界面错误行。真实卸载、重新准备与恢复验收由父任务安装提交版本后执行。

## 工作区与收口
- 工作区：`C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/integration-worktree`；分支 `codex/spug-backup59-mvp-integration`；基线 `f2cff77bf13492de9ede64f60001a02e054190c2`。
- 本地未执行构建、发布、服务器写入、worktree 合并或删除。实现与记录分别精确提交；融合和工作树收口由父任务负责。
- 实现提交：`f0b143ae539577ad2c1bb6e7633b5e2ff401e2f4`；仅 7 个本任务产品、测试、安装说明文件。
