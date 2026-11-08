# 增量 SQL 有界读取

## Current Status
ready_for_closeout — 本子项实现和本地验证完成；尚未提交，实际封包映射、Linux 内存限制测试、集成与最终收尾由主任务统一执行。未访问服务器、未执行备份或恢复。

## 目标
消除增量恢复 `expanded.read_bytes()` 对整份展开 SQL 的内存需求，保持现有前缀、BINLOG、GTID、空增量和 FILE_POSITION/DDL-only 判断，以及完整归档摘要与作用域校验。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。读取、超时、guard、文件变化和格式错误均显式失败。
- 是否从根因和长期维护角度解决：是。采用有界扫描器，以固定内存识别跨块标记及不定长 GTID 空白/数字，不依赖文件大小或整行长度。
- 是否存在临时补丁或绕过：否。保留现有 gzip 展开和完整摘要验证；不修改归档格式、不删除 raw 载荷、不改变恢复链。

## 经验门禁
- STANDARD 来源是冻结包加 reviewed transforms，LIGHTWEIGHT 来自当前映射；两条交付路径必须包含相同扫描器及真实调用。
- 不用源码字符串存在代替实际调用；本地测试需执行真实文件扫描及包内方法到导入边界。
- 运行期限覆盖 guard 和读取；跨块 BINLOG 与 GTID 标记、任意长度空白及数字必须与原正则含义一致。
- 测试文件只在独立临时目录；不读取私密输入、不访问服务器、不运行 Docker、不提交。

## BDD
- Given 有正确前缀且 BINLOG 标记跨读取边界的真实文件；When 扫描；Then 与原字节搜索结果相同且每次读取有界。
- Given GTID_NEXT 的空白、十六进制/连字符或数字跨任意多个块；When 扫描；Then 正确接受完整标记并拒绝截断/错误标记。
- Given 空增量或 FILE_POSITION 的 DDL-only SQL；When 恢复入口检查；Then 不要求 BINLOG/GTID 标记，原 scope 与摘要校验保持。
- Given SQL 大于可用内存；When 独立进程扫描；Then 内存增长与文件大小无关。Linux RLIMIT 由主任务统一安排，本地只记录实际文件验证结果。
- Given guard 拒绝、期限耗尽、读取失败或输入变化；When 扫描；Then 立即暴露原失败，不进入 SQL 导入。

## 里程碑与验证
- [x] RED：实际旧入口对真实文件仍整体读取，新的流式需求测试失败。
- [x] GREEN：扫描器及两套恢复入口正确通过文件、边界与异常测试。
- [x] REGRESSION：相关 SQL 性能单元测试通过；主任务仍需统一检查实际包、Linux 内存约束及真实恢复。

## BDD / TDD 执行证据
- 环境准备：指定 Python 原先缺少 pytest/jsonschema，首次测试未能启动，不计作 RED。按主任务授权，复用本任务 wheel 缓存，补充官方 PyPI 的 Windows `rpds-py==0.22.3`，仅安装至本任务私密 `test-dependencies`。测试使用 pytest 8.3.5、jsonschema 4.23.0，不修改全局环境。
- RED：`python -B -X utf8 -m pytest scripts/tests/test_incremental_sql_stream.py -q -p no:cacheprovider` → FAIL。24 MiB 真实 SQL 经真实 staging / gzip 展开进入原 `NativeData.incremental_captured_sql`，扫描阶段峰值 25,180,720 bytes，超过 8 MiB 上限。为了定位本次根因，计量在真实 gzip 展开后重新起算；先前 JSON 读取器自身的固定 64 MiB 分配不在本修复范围内。
- GREEN：同命令 → PASS，初版 105 项。验证真实文件、跨块 BINLOG、GTID 任意长度空白/ID/数字、2,000 个确定性随机正则对照、两种引擎的实际方法、DDL-only、空增量、错误模式、guard 拒绝、超时、文件变化和读取错误。
- RED：`python -B -X utf8 -m pytest scripts/tests/test_incremental_sql_stream.py::test_deadline_includes_final_marker_parse -q -p no:cacheprovider` → FAIL，最终标记解析延时后未重新检查期限。使用真实文件和真实解析器，仅在解析器调用边界增加可观测延时。
- GREEN / REGRESSION：`python -B -X utf8 -m pytest scripts/tests/test_incremental_sql_stream.py scripts/tests/test_backup_performance.py -q -p no:cacheprovider` → **152 passed, 2 skipped in 17.80s**。本子项 106 项全部通过；两个已有回归用例明确要求 Linux fcntl/inode 和原生 Linux 路径，Windows 未执行，不能视为通过。
- 独立进程实际扫描约 26 MiB SQL 和跨块长 GTID 空白，并禁止调用 `Path.read_bytes`；扫描峰值小于 8 MiB。此证据不替代 Linux RLIMIT 或真实数据库恢复验收。
- `git diff --check` → PASS。STANDARD `common/recovery_data.py` 的完整展开摘要校验保留；只替换标记读取代码，不替换冻结恢复模块或更改作用域验证。

## 集成交接
- 新增 `ops/recovery/recovery_sql_stream.py`，STANDARD 命名 transform 自动加入 `common/recovery_sql_stream.py`；主任务负责 LIGHTWEIGHT 的 `files.json` 映射及封包差异允许表。
- `standard_fixes.py` 本子项仅新增 `incremental_sql_stream(payload, root)` 和 `apply` 开头的一处调用，没有修改控制平面复制清单。
- 待主任务记录：真实封包校验、Linux 专项、整体自动增量验收、提交和 closeout。本子项没有单独提交或清理任务工作区。

## 归档优化建议
当前 raw SQL 和 gzip 双份归档属于已固定恢复合同，直接删 raw 会导致恢复拒绝。后续采用显式新载荷版本、展开内容摘要及新旧读取兼容后再省去归档 raw。镜像当前已有按 ID 校验的导出缓存，每个备份独立保存 tar；跨包复用需要依赖保留和完整恢复合同，不能通过硬链接或省复制单独实现。
