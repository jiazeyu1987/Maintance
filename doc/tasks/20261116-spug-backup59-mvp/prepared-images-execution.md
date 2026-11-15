# 已准备目标镜像合同收敛

## Current Status
ready_for_closeout

## 目标、里程碑与预期验证
v10 真实全量恢复在 1.508 秒通过准入，随后 target-checks 以 ARCHIVED_IMAGE_VERSIONS_INCOMPLETE 失败且未写入。父任务已确认准备流程按所选 roleImages 创建五个服务并读取实际镜像 ID，但目标 application.imageBindings 为空。本轮只核对实际版本绑定消费合同，选择最小正式修复，BDD/RED/GREEN 后提交；不部署、不操作服务器。

## 经验门禁
- 前一去重任务已提交交父任务，远端真实失败保留；本轮不得把失败改成功、自动重试或安装新镜像。
- 真实镜像来源以已选 roleImages 和创建后实际 inspect 为准，避免重建旧历史映射体系；保留机器/容器身份、源/NAS隔离和同目标互斥。
- 只在 integration-worktree 修改明确相关文件；父统一记录共享命令日志、部署和真实 UI 验收，私密证据不提交。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；复用准备时已明确选择并核实的镜像，错误仍明确失败。
- 是否从根因和长期维护角度解决：是；对齐新目标构造与实际执行合同，避免旧元数据结构成为重复门禁。
- 是否存在临时补丁或绕过：否；只通过正式构建/配置路径交付。

## BDD
Given native 已按所选备份点 roleImages 创建目标并记录五个实际 imageId，When preparedEmptyTarget 在恢复前检查应用输入，Then 使用这些已登记实际服务镜像，保持实际镜像漂移拒绝，不依赖空的旧 imageBindings 映射；非准备目标保持原合同。

Given 同一已准备目标的旧 configurationBindings/artifactBindings 也为空而真实只读挂载已创建，When 检查应用输入，Then 复用实际 bound 挂载合同，不重建旧映射；backend/frontend 启动角色仍必须完整。

## 证据与实施
- 原任务 full760a8c7c23594a4dbb40ee0f0748b394，history394；admission 1.508s 成功、target-checks 0.536s 失败，mutation 未派发。失败记录未改写。
- 既有 inventory59.private.json 模板与实际 v10-application-contract-shape.private.json 均确认 imageBindings/configurationBindings/artifactBindings 为零，startOrder=['backend','frontend']。只读取小型结构，没有附件扫描或凭据输出。
- 正式 standard_fixes.prepare_target_bind_mounts 增加 prepared application_inputs 分支：保留启动顺序合同，然后返回。实际服务的镜像 ID 和挂载继续由原 bound 在恢复/启动前核对；非 prepared 路径不变。
- native 不需要变更；正式生成部署差异仅 common/recovery_minimal_runtime.py，加其 package.json 文件摘要及 packageSha256。父任务从新提交固定 release 构建/安装，不改旧引擎目录。

## TDD
- RED: 既有隔离 Docker Python/pytest，`python -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_backup_target_mounts.py -k prepared_inputs` → 1 failed, 5 deselected，精确 ARCHIVED_IMAGE_VERSIONS_INCOMPLETE。
- GREEN / REGRESSION: 同一现有运行环境执行整个上述小测试文件 → 6 passed（1.90s）。覆盖 prepared 空映射可用、缺启动角色拒绝、非 prepared 原映射继续拒绝，以及原实际 Image 漂移与数据挂载边界。
- 未安装新依赖，未操作服务器/容器。git diff --check PASS；真实恢复结论仍由父任务 UI 验收取得。
