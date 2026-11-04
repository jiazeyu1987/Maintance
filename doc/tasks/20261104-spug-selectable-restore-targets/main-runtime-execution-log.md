# 主实例安全数据恢复执行合同

## 范围与经验门禁
- Trigger：安全模式恢复已存在的三服主实例；本子任务仅本机代码与单元合同验证。
- Preflight check：已读 AGENTS、task.md、design.md 和冻结安全引擎；保留档案字节、SQL/对象/Redis 校验，不替换容器配置或程序镜像。
- Blocker：镜像与档案不兼容、存储/网络/写入者专属权不明、配置或身份漂移必须阻断；当前未授权远端安装及恢复。
- Verification：同服需显式 main + replacement v2；归档镜像精确兼容；主实例固定身份、配置、网络、存储在破坏前及安全引擎阶段反复核验；旧演练目标保持原合同。
- Forbidden action：不操作服务器，不执行真实恢复，不将单元合同验证写为实际恢复成功，不把演练隔离校验直接关闭。
- Evidence：本文件、test_main_restore_target.py 与 standard_fixes.py 的上下文固定补丁。

## BDD
- BDD: 注册主实例 -> Given 显式主实例合同、replacement v2 和专属资源证明，When 选择同源服务器，Then 允许进入同一安全数据引擎，并核验固定程序而不修改程序配置。
- BDD: 不兼容归档 -> Given 当前 backend/frontend 镜像与选中备份不同，When 破坏前准入，Then 失败，禁止清库/停止程序。
- BDD: 环境漂移 -> Given 容器配置、网络成员、存储或配置文件变化，When 任一后续 bound，Then 暴露失败并保留现场。
- BDD: 未登记目标 -> Given 普通演练配置或无专属资源证明，When 同服请求，Then 保持旧拒绝或明确阻断。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，新增版本化主实例合同替代演练资源假设，数据引擎原有读取与回读保持。
- 是否存在临时补丁或绕过：否。

## TDD
- RED: bundled-python unittest 收集最初因缺 jsonschema 失败，按真实依赖处理；复用任务隔离依赖后再次执行 -> ModuleNotFoundError: recovery_main_target，证明正式主实例合同尚缺。
- GREEN: 新合同首轮 18 tests PASS；覆盖明确 v2、同源 UUID、镜像不一致、writer 证明 scope、配置字节、网络/运行状态漂移、旧演练委托和每次 bound 存储复核。
- RED: 主实例 MySQL query/ALTER 测试 -> mysql_query 缺失、原路径仍依赖 /run/recovery/mysql-client.cnf；真实主库没有该演练文件。
- GREEN: 主实例命令仅改用 stdin→MYSQL_PWD，密码不进入 argv，--no-defaults 禁止额外登录输入；演练路径保持。安全 SQL import 原有 stdin 密码与分块 SQL/校验和协议保留，并在冻结安全包实际 import 后验证。
- RED: 追加同服对象端点/客户端 IP 准入 -> object_endpoint 缺失、服务 IP 未绑定实际附件。
- GREEN: 主实例只允许登记 MinIO 的固定地址；普通演练保留源端点拒绝。数据角色 IP 必须出现在自身固定网络附件。
- REGRESSION: Windows bundled-python -m unittest discover -s scripts/tests -p test_main_restore_target.py -> 28 tests PASS。
- REGRESSION: 本机 Docker python:3.12-bookworm 仅只读挂载工作树，安装真实 Linux jsonschema==4.23.0 后运行同一 unittest -> 27 tests PASS（随后追加纯 physical_mount 委托合同测试，最终 Linux 结果见后续记录）。
- REGRESSION: 最终本机 Linux 同一命令 -> 28 tests PASS，0 skip；临时容器 --rm 已退出，无服务器连接或数据卷修改。
- RED/GREEN: 最后合同审查新增同容器不可担任两个角色 -> RED 未拒绝重复 ID；增加独立角色 ID 约束后 Windows 29 tests PASS。
- REGRESSION: 最终 Linux 29 tests PASS，0 skip；安全包实际补丁、导入及完整性合同一并通过。
- 早期 Linux 验证分别暴露依赖跨平台 rpds 扩展、tmpfs noexec 与测试字符串转义问题；改为容器自身安装 Linux 依赖并修复测试比较后通过，没有跳过失败项或修改安全校验。

## 实现与验证范围
- 新增 RegisteredMainApplication/v1 与 RegisteredMainWriterCustody/v1；提供只读观察生成器 capture_main_application 和控制层无凭据 observe_main_target。
- host 网络允许正常其他成员，自身附件与配置必须固定；bridge 网络允许显式登记 ambient 成员，后续成员变化拒绝。不能把网络成员枚举当作数据库/对象/Redis 独占证据；独占证据另行明确登记。
- 安全引擎执行同一 full/incremental database、physical object apply/hash/export/compare、Redis 与健康流程。仅替换原演练专用的源 UUID 排除、空资源/隔离/标签假设；主实例由明确 v2 存储所有权和固定配置网络核验替代。
- standard_fixes 固定上下文应用成功，实际提取安全包并在新子进程导入，确认安全数据回读、物理 compare、应用健康和档案 hash 检查仍有效。
- 未连接服务器，未执行真实覆盖，未声明三服可恢复。实际只读存储/写入者/配置证明缺失会阻止登记；实际恢复与安装需要主任务处理对应授权及验收。
