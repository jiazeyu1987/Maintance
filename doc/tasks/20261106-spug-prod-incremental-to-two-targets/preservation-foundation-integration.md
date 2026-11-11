# 覆盖前保全与归档输入基础实现集成

## Current Status

in_progress。原分工实现已冻结，父集成只包含本任务的已验证基础模块、控制接缝与依赖；未实现的保全 HTTP/UI/执行分派留在后续范围，不能声称已可跨服恢复保全点。

## 目标、里程碑与验证

1. 汇合真实普通归档输入重建、保全原件递归元数据、覆盖前自动保全 producer 和两种引擎构造。
2. 按原始证据核核心 producer 字节保持；保全来源与输入模块用各自最终有限协议证据，不把旧 producer 当新整个包已通过。
3. 对最后补入的两输入模块执行实际候选独立导入及 lightweight 清单 RED/GREEN/回归，精确提交基础实现。
4. 后续从该已提交内容创建本次新发布 worktree，正式封包与必要实际候选验收通过后才允许安装；此阶段不改运行服务。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。所有原路径、身份、原件、预算、SAFE 和来源/目标准入保持；缺新合同明确失败。
- 是否从根因和长期维护角度解决：是。完整目标保全和输入确定重建由正式模块与构造提供，不由 Codex 手写单点配置。
- 是否存在临时补丁或绕过：否。没有修改旧备份或签新旧 checksum，没有复制运行目录或源码兜底。

## 经验门禁

- Trigger：同链多分工实现集成和正式封包依赖变化。
- Preflight check：精确路径/归属；逐实现现有 RED/GREEN 原件；实际模块来源；核心 producer 源字节与 r6 快照比较；新依赖候选严格导入；暂存只含本任务实现和直接测试。
- Blocker：未知改动、依赖缺件、必要测试失败、私密日志或未经验证的业务执行分派混入即停止提交。
- Verification：diff-check、精确 staged 清单与源码 pins、原必要证据和最新 12 项实际候选回归；正式发布另有新提交 worktree 和运行验收。
- Forbidden action：不整体暂存任务目录、不提交 PRIVATE/凭据/运行日志，不把 metadata-only 结果、有限外部协议或旧 candidate 当现场恢复成功，不改业务服务或共享盘。
- Evidence：stage2b-ordinary-linux-r1、preservation-owner-c2-red-plan、main-preservation-source-pagination-tdd-log、main-preservation-packaged-producer-native-r6、restore-input-dependency-verification-r1。

## 已核验证据的准确范围

- ordinary A1/control 接缝：实际 Linux 30 项、Windows 相邻 104 项通过；核心三个文件当前 SHA 与记录相同。
- C1/A1/C2：113 项通过；当前 consumer 为 49186 B / 7442a0f4b4b7e9faec1842cede5b8e87cf0cab45e12bfb4d8ad3c76aaeba3ef9，符合最终记录。
- producer r6：实际 STANDARD 完整有限协议 1 项通过。当前 preservation/capture/materials/support/runtime 五核心文件与原生产源快照逐字节相同；当前 consumer 和 builder 已有后续变更，故不声称整个新包已由 r6 验收。
- 最后依赖修复：STANDARD 2 个未声明依赖 RED、lightweight 2 个缺映射 RED；首 GREEN 因本机缺 jsonschema 3 FAIL/9 PASS 原样保留，PRIVATE 按既有 jsonschema4.23.0/redis5.2.1 补依赖后完整 12 PASS/0skip/native0，16.766秒，六输入原件保持。
