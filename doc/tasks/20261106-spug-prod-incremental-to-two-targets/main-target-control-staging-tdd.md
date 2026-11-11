# 独立目标文件暂存 TDD

## Current Status

ready_for_closeout；独立入口、33项真实临时文件系统测试及108项相邻回归通过，已通知父任务最终审查，待父任务显式提交。仅新增本实现、测试和本文，不改旧 stage/all-role 合同，不提交或访问服务器。

## 目标、里程碑和预期验证

1. 明确入口签名和首写前完整预检，核对旧辅助函数实际合同。
2. BDD→RED：新目录成功、候选或字节漂移/别名/已存在路径首写前拒绝、部分写入失败原件和已创建文件保持。
3. GREEN→REGRESSION：本地临时目录独占创建153 payload+原始package.json共154包文件+16文档，0400、全部pin与原件保持；相邻旧入口与新纯候选合同回归，不操作真实三服目录。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；失败明确报告，不自动删除部分结果。
- 是否从根因和长期维护角度解决：是；独立目标文件暂存承接153件新包，原147/all-role合同保持。
- 是否存在临时补丁或绕过：否；不跳过严格重建或首写前检查，不授予runtime/安装权限。

## 经验门禁

- Trigger：目标文件暂存、独占新目录、包与配置固定字节。
- Preflight check：严格重建候选等值；旧新manifest/全部成员compile/pins；原owner/control实际字节；新engine/configuration规范路径与所有祖先无软链、别名或已有新路径；首写前完成全部输入核验。
- Blocker：原件/候选/包漂移、路径别名/冲突、任何不完整前置材料，首写前拒绝；写入后失败保留已创建路径与明确错误。
- Verification：RED→GREEN→REGRESSION真实临时目录文件操作与Linux0400/softlink，记录原生退出、数量、模式、字节和失败路径。
- Forbidden action：不改旧stage合同，不创建mount/reload/receipt/selection/restore，不连接服务器，不删除失败已创建路径或覆盖旧文件，不把FILES_STAGED_RUNTIME_UNVERIFIED当安装成功。
- Evidence：父 `main-final-target-upgrade-plan.md` 独立目标文件暂存范围，新纯候选101项回归和3组真实只读纯重建。

## BDD

- Given 严格可重建候选、固定包与全新目标根；When 文件预检后暂存；Then 仅新engine/configuration根独占创建153 payload及原始package.json、16文档，0400/字节一致、原目录保持，返回FILES_STAGED_RUNTIME_UNVERIFIED。
- Given 候选/包/pin漂移、原件改变、已有新根或软链别名；When 暂存；Then 首写前拒绝，目录树保持。
- Given 完整预检已通过但独占写入中发生真实错误；When 暂存；Then 报告已创建路径与失败位置，保留原件及部分结果，不清理重试。

## 执行证据

- UTF-8 bootstrap：已识别父任务与前一子任务ready_for_closeout状态，读当前计划/经验索引/PowerShell规则；暂存子任务不依赖前一任务的安装收尾。
- 入口签名已获父任务确认：`preflight_target_filesystem` / `stage_target_filesystem(*, candidate, host, current_controller, owner, control, old_build, new_build, preservation, configuration_root, new_engine, package_raw, previous_package_raw)`。
- 父任务明确正式manifest属于运行依赖：新engine落原tgz原始package.json，输出payloadFileCount=153/packageFileCount=154/documentCount=16；首写前旧engine全部147payload及package.json必须核对原包字节，不能省略metadata。
- 已核旧辅助：`_parent_without_alias(path)`检查最近已存在祖先不是软链且resolve精确相同；`_directories(path,created)`仅对缺失目录逐层700独占创建；`_write_exclusive(path,raw,created)`使用O_EXCL/O_NOFOLLOW、0400、fsync及严格回读/uid/nlink核验。复用不修改旧模块；完整预检、新根独占创建和失败留存由新入口包住。
- `target-control-staging-red-r1`：测试载体fixture路径重绑定只替换PYTHONPATH首项，旧planner正确拒绝其余外来engine，导致30 setup errors/native1。属于测试载体错误，不作为产品RED；已修正fixture完整路径重绑定，生产文件仍未创建。
- `target-control-staging-red-r2`：fixture全局替换误将control模块目录名当根前缀，30 setup errors/native1；仍为载体错误，不算RED。改成逐PYTHONPATH项的严格根前缀替换。
- RED：`python -X utf8 -B PRIVATE/run-target-control-staging-linux.py red-r3` → native1，30 failed in 0.85s，全部命中 `MISSING_TARGET_ONLY_FILESYSTEM_STAGING`，setup已通过；此后才创建生产入口。
- GREEN：同隔离入口 `green-r1` → native0，30 passed in 2.16s；真实Linux临时目录154包文件+16文档的0400/内容/独占创建及旧150原件保持通过。
- 补充RED：`red-r4` → native1，1 failed/32 passed in 1.90s；故障注入将已成功写入首文件改为0600，最终复核未拒绝。最小实现补充最终每文件0400/uid/nlink复核，既有独占写入辅助不改；同时原件写入期间变化和policy写入失败的两个负向用例已通过。
- REGRESSION：`python -X utf8 -B PRIVATE/run-target-control-staging-linux.py regression-r1` → native0，108 passed in 2.54s（新暂存33、新candidate54、旧stage相邻21），0skip/0warning，stderr=0。载体14.797s，固定镜像 `sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735`、原12枚wheel不变；network none、readonly、cap-drop ALL、pids128、512MiB、cpu1、256MiB/64MiB有限tmpfs、600s总进程期限。原始输入未变，容器已清理，remoteWrites=0、actualBusinessRestore=false。
- 最终source快照：`PRIVATE/target-control-staging-regression-r1/source.tar`，608文件/9502720B，SHA256 `6508a352809b4dd1e393f89a92ee8d38d9987e0ee5749d0ba644dbd3618b01f8`；原始结果/日志/manifest保留同目录，未写真实三服目录。
- 实际双原包验证：`python -X utf8 -B PRIVATE/verify-target-staging-actual-package-r1.py` → native0，1.031s，旧147payload+metadata=148，新153payload+metadata=154，固定6新增23改变0删除，原件字节保持。正式新metadata16473B，SHA256 `a161066c977a4adffda7274aec0906f46c6c3e00e41f18fd02f87b9b6a1bc933`；只验证包，无文件暂存或服务器访问，摘要在 `PRIVATE/target-staging-actual-package-r1-result.private.json`。
- 实现pin：10246B，SHA256 `b35a3f984301514904c7c4beb932e0682d47790dd4acb8a988228c8b67eaacfd`；不修改旧模块。完整预检先严格重建候选，再验证所有170目的路径和150旧原件，任何预检失败零新写入；部分写入异常保留 `created_paths`、`failed_path` 与原始 `__cause__`，禁止自动清理重试。
- 首写前/写后文件保护为静态文件合同；物理锁、运行进程/容量/挂载/业务保持必须由父任务外层真实门禁负责，本入口不会声称完成安装、reload、receipt、selection或恢复。
- 本任务3个文件UTF-8无BOM、compile及逐行空白检查通过；仅3个新文件，无提交。共享日志与整体任务状态由父任务更新。
