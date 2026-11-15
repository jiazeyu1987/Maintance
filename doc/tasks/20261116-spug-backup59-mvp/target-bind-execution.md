# 空恢复目标与标准包挂载合同

## Current Status
ready_for_closeout。最小实现和本地定向验证完成，父任务负责统一提交与远端安装验收。

## 目标与里程碑
只在正式 standard_fixes.prepare_target_bind_mounts 适配新准备目标的三个数据 bind，父任务负责 apply 调用与提交；native 生成 preparedEmptyTarget 标记。完成 Given/When/Then、RED、最小实现、Linux 定向 GREEN 后交父审。不执行远端或部署。

## 经验门禁
- 使用 standard_sources()+safe_fixes 的实际生成代码，不用轻量源码代替标准合同。
- 只放行机器准备模块生成的明确目标、dataRoot 内精确登记的三项数据目录；保留源/NAS分离、实际容器身份、内部网络及共享检查。
- readonly工具/私密挂载沿原合同；旧volume和非prepared目标行为保持。
- 私密证据只读取路径和挂载元数据，不读取/记录口令，不改业务容器。
- 本地测试可复用既有 Docker python:3.12-bookworm 与既有pytest依赖，network none，只读挂载工作树；本地协议边界测试不等于服务器恢复验收。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。用户要求最小恢复，父批准明确prepared目标跳过旧iptables依赖与规则；普通旧目标仍保持原合同。
- 是否从根因和长期维护角度解决：是。生成配置与标准恢复入口的bind格式正式对齐。
- 是否存在临时补丁或绕过：否。正式打包变换及生成字段随源码提交。

## BDD
- Given preparedEmptyTarget=true 且三个RW bind分别位于dataRoot/mysql、minio、redis并精确列入dataPaths，When标准bound/fresh_target/physical入口检查，Then允许并保持空目标和共享检查。
- Given未登记、越界、角色/目的地不匹配、源/NAS重叠或其它容器共享bind，When检查，Then拒绝。
- Given只读工具配置或旧volume，When检查，Then保留原合同。
- Given明确prepared目标，When初始化和bound，Then不再要求不存在的旧iptables可执行文件/规则，但继续核身份和内部网络；普通目标仍要求原iptables。

## 现有证据
full-running-location.private.json实际dataRoot为/mnt/intruoyi-data/spug-empty59-9ad0f898afb1。v10-target-mount-contract.private.json实际数据三个bind为mysql→/var/lib/mysql、minio→/data、redis→/data，RW=true；七个recovery-tools/private文件和两个target/config文件均RW=false。dataPaths精确列三个数据目录、target/config、recovery-tools/private。

标准生成runtime原bound无条件拒绝可写bind，fresh_target只接受volume，physical_object_chain再要求MinIO volume。readonly路径均已在允许范围，不能把private/tool扩大为可写范围。新标记由native生成，不接受浏览器请求指定。

## 实现与验证

- `standard_fixes.prepare_target_bind_mounts` 只改标准生成runtime三个实际冲突点。`prepared_data_bind` 要求preparedEmptyTarget为true、角色mysql/minio/redis、精确dataRoot/role、该路径精确列入dataPaths、真实RW bind与对应目的地，并继续拒绝源/NAS重叠。普通volume沿原inspect流程；容器共享检查保留。MinIO bind不读取不存在的Name字段。
- preparedEmptyTarget由native.fresh_target生成。仅明确准备目标省去已知不存在的旧iptables执行器与旧规则；非prepared目标保留旧行为，机器/Docker/container/Internal bridge检查保持。
- readonly工具/私密配置已被原dataPaths合同允许，fresh_target只遍历RW挂载；无需新复制、权限扩大或处理readonly路径。
- RED：已有Docker python:3.12-bookworm、只读工作树和既有local-test-deps、`--network none --rm`执行`python -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_backup_target_mounts.py`，5 failed。确认错误为缺helper、WRITABLE_HOST_BIND_REJECTED、SHARED_TARGET_DATA_VOLUME、DEDICATED_MINIO_DATA_VOLUME_REQUIRED，以及prepared仍要求iptables。首次本地测试载体缺machine-id/Network inspect列表问题已纠正后重新取得上述业务RED，不计载体错误为产品证据。
- native marker RED：`-m unittest ops.spug.test_prepare_target_native.NativePreparationTests.test_owner_uses_new_resource_identities` -> KeyError preparedEmptyTarget。
- GREEN：native整模块25 tests PASS；同Linux挂载脚本5 passed in 1.90s。测试执行standard_sources()+safe_fixes生成方法的真实分支，明确替代Docker/SQL协议边界；真实临时数据目录参与路径与空目录检查。物理测试在到达实际复制调用前用显式异常探针终止，验证bind准入及共享拒绝，不宣称完成真实恢复。
- 父将prepare_target_bind_mounts加入正式apply最后、physical_restore_reads之后；本子任务未改其物理复制去重函数或apply调用。
- 未进行新远端采集、服务器修改、部署、恢复或Git提交。父任务继续实际环境验收与提交收口。
