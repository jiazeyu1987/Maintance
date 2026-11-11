# 目标采集 Redis 认证合同

## Current Status

ready_for_closeout；本子项实现及必要验证已通过，待父代理复审并按总任务集成提交。未自行提交、安装、访问服务器或执行实际业务备份/恢复；总体目标完成与正式封包由父任务另行验收。

## 目标与里程碑

1. 先用可观察的静态准入测试固定 v1 密码配置失败及 v2 显式认证边界（RED）。
2. 最小整理目标采集认证合同，接受已登记的 v1 密码、v2 PASSWORD/NONE，错误明确失败（GREEN）。
3. 执行相邻本机回归，报告最终文件和证据，交父代理复审提交；新字节需重新正式封包。

## BDD 与预期验证

- Given v1 且精确登记 Redis 密码 pin；When 目标采集配置准入；Then 接受同一 pin，拒绝缺失、错误或未登记凭据。
- Given v2 显式 PASSWORD 或 NONE；When 准入；Then 仅接受登记模式与凭据一致，NONE 不允许携带秘密。
- Given 未知 schema、v1 夹带 v2 声明、v2 缺少或未知认证字段；When 准入；Then 明确拒绝，不选择默认模式。
- RED→GREEN→REGRESSION 以实际命令及原生退出码记录；低层静态合同测试不代表实际服务器备份或恢复通过。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否，不从未知声明猜测模式，不补空密码。
- 是否从根因和长期维护角度解决：是，目标采集遵循已存在的 MAIN v1/v2 认证合同。
- 是否存在临时补丁或绕过：否，不改变实际 Redis 配置迁就采集代码。

## 经验门禁

- Trigger：新增 MAIN target capture 与既有 v1/v2 原生目标合同不一致。
- Preflight check：先核现有 validate/redis_password 合同、目标采集入口及原测试；只改认证相关源码和新测试。
- Blocker：错误版本或秘密 pin 无法明确绑定、相邻验证失败，禁止提交或宣称交付。
- Verification：BDD、实际 RED/GREEN/REGRESSION、diff 与 UTF-8 复读；正式封包及三服验证由父任务另核。
- Forbidden action：不补默认认证、不改服务器、不绕过原文件或运行身份保护、不夹入无关改动。
- Evidence：本页、父任务 main-final-target-upgrade-plan.md 与后续 PRIVATE 原生命令日志。

## 执行记录

- 已读索引及 PowerShell UTF-8 前置规则；适用经验为实际封包配置传递及原 MAIN 合同保持。正式包验证不得外推到本次新字节。
- RED: Windows Python -X utf8 -m pytest -q -p no:cacheprovider scripts/tests/test_recovery_target_capture_redis.py -> native1，31 FAIL，集中认证合同函数缺失；属于新合同 RED，不冒充实际旧入口失败。
- GREEN: experience-preflight -> PASS（本机隔离 Linux 静态入口协议测试）：原镜像仅以当前实读 image id 使用，无网络、只读根、cap-drop ALL、pids/memory/CPU 限制；源码和离线轮子只读固定，临时测试文件限定 tmpfs，零服务器访问/业务命令。输入前后 SHA 与容器清理单独核对，失败原件保留。
- Linux red-r1 环境失败：RPDS 的真实 Linux 扩展无法从 Docker 默认 noexec tmpfs 映射；collection ERROR/native2、0业务节点，不作为产品 RED。输入保持、容器移除。red-r2 仅明确允许隔离 tmpfs 执行 Python扩展与有限协议工具，不变更产品或目标时限。
- RED: 本机 Linux red-r2 -> 3 FAIL/2 PASS/native1，真实 `_configuration` 静态准入方法重现 v1 合法密码及缺密码均 KeyError，未知 v2 认证缺乏专门声明错误。11.282秒，输入保持、容器移除；零服务器操作、非 MAIN 构造或恢复验收。
- GREEN: Windows 新合同31项+原 Redis 5项 -> 36 PASS/native0/3.46秒。
- GREEN: 本机 Linux green-r1 -> 实际静态准入5项+新合同31项+原Redis5项=41 PASS/native0/5.65秒；原生载体14.984秒，输入保持、容器移除、stderr0。helper 与入口连接均通过；原完整 MAIN 准备回归另行进行。
- 产品仅修改 recovery_target_capture.py：新增纯函数 `_redis_authentication(target, redis_snapshot)`，以既有 v1/v2 版本合同严格准入，入口保留原容器/IP/库/文件/资源检查后调用。未改变认证、备份范围、运行限额或安装配置。
- REGRESSION r1 载体缺文件：原配置测试的 fixture 导入链还读取 build_variants.py，原快照仅含 formal/recovery/tests，collection ERROR/native2、0业务节点；未作为产品失败或成功。输入保持、容器移除。r2 把真实 backup_engine Python 模块纳入原始 SHA 快照，不修改原 fixture 或伪造构建结果。
- REGRESSION: 本机 Linux regression-r2 -> 54 PASS/0FAIL/0ERROR/0SKIP/native0，pytest2.11秒、完整原生载体10.312秒。其中原 MAIN 配置准备13项、新实际静态准入入口5项、新纯认证合同31项、原Redis5项；不把前一轮41项重复相加。源输入351件全部前后保持，隔离容器移除、stderr0、remoteWrites0。
- 最终差异检查：git diff --check 通过；产品仅31行新增/5行删除，原UTF-8及LF方式保持，未转换原文件编码。三个修改/新增源码均 UTF-8 严格读取与 compile 通过。

## 最终交付与证据

- 产品：ops/recovery/recovery_target_capture.py（29788B，SHA256 f934dc11c0b0d1348500e16afadb961447858edbdd788321aa231cd2e0cbe5c4）。
- 静态合同：scripts/tests/test_recovery_target_capture_redis.py（4485B，SHA256 50e6a267d52cafb5f67323f9a2ba68ad065bdfb25f73b6feca8ce2bdc4cd83de）。
- Linux实际静态入口：scripts/tests/test_recovery_target_capture_redis_entry.py（6079B，SHA256 aeadc012e98f0063e8c7422b9f8bba60fb96b3152a9e666d5a0cac0d9c3529f4）。
- PRIVATE证据目录：C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/target-capture-redis-contract-{red-r1,red-r2,green-r1,regression-r1,regression-r2}/。每轮含 result.private.json、原 stdout/stderr、只读 SHA 快照及清理结果；旧失败不覆盖。
- 最终 regression-r2 源快照：6553600B，SHA256 a332b0cf1e1cd230bfe3fc673389d8475f1d21f24775aa0fda239195ec184e9a；stdout 99B，SHA256 37e112e77ecaf5ab0ec9958488ac318995f6302909c91cbc1933127efa28c372，stderr0。
- helper 的输入快照须先经 source_config_redis 验证 shape/pin；实际 _configuration 保留此既有前置检查。helper 仅校验声明和同一登记 pin，不授权启动、停写、归档或恢复。
- 未创建 worktree、未启动业务控制台或长期服务，所有本子项隔离测试容器均已移除；PRIVATE 原件保留。父代理须重新提交/构建新产品字节，不把172566c旧包验证外推到本次修改。
