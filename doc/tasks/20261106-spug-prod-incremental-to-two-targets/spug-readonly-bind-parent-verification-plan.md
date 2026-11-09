# Spug continuation 父独立验收计划

## Goal and Current Status

prepared_not_executed。子代理尚在TDD，父不执行不稳定源码或真实apply。冻结后独立核验正式c1的纯准备、源码边界和实际嵌入执行能力，再限定提交并进入真实配置发布。

## Milestones and expected verification

1. 核真实RED/GREEN/REGRESSION原始日志、实际退出、零skip及冻结源码前后SHA；原v2 publisher字节保持，三个reader改动仅批准接缝，原HOST/SPUG程序常量及生成合同保持。
2. 独立运行新增continuation与受影响v2 reader/publisher、selection、closeout合同，保留私密原始输出及实际报告，不在工具输出打印配置或凭据。
3. 用正式c1运行纯prepare；不得创建apply claim/attempt或调用传输。正式原件、2份原源码及284不变输入、资源安装/真实mount/原进程终态全部核验。
4. 使用已核18080原容器的原Python执行只读guard；固定同一entry/旧空audit/原目标状态，保存真实程序、原生退出和前后容器snapshot。只读检查不等于安装通过。
5. 若需要验证动态嵌入程序的真实Linux文件行为，使用原容器已存在的精确镜像创建本任务独立一次性测试容器：覆盖entrypoint为python3，network=none、read-only root、cap-drop=ALL、no-new-privileges、内存256MiB/pids64，仅两个明确路径使用16MiB tmpfs，不挂宿主目录、Docker socket、凭据或业务数据。显式合成的七文件合同fixture只验证本地原生保全/volume原子替换/readback/拒绝，不冒充E2E或真实服务器。程序来自最终冻结源码，保存输入/输出及真实退出，结束仅删除本任务该独立容器并核已不存在。
6. 所有必要验证通过后限定实现提交；实际c1发布另记experience-preflight，严格原顺序和全保全屏障，原三次host-publish不重跑。配置发布后继续完整真实UI与恢复验收。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。失败保留原始证据，不用延长预算或fixture成功替代现场结果。
- 是否从根因和长期维护角度解决：是。覆盖宿主与实际Linux动态生成程序的执行边界，防止只解析源码而遗漏运行依赖。
- 是否存在临时补丁或绕过：否。隔离fixture与真实c1分开计量，不修改产品/控制代次、原失败或原mount。

## 经验门禁

- Trigger：任务发布器在只读bind与volume之间明确续办、动态嵌入程序和真实文件调用。
- Preflight check：冻结源码/实际原件及批准边界、原测试真实终态、明确两实例和镜像、隔离容器归属及限制、真实只读guard范围。
- Blocker：源码仍变化、旧断言被削弱、缺真实报告/退出、任何不明确存储或进程状态、隔离资源不能限定或无法清理。
- Verification：独立测试及原生实际结果、源码/输入pins前后保持、0skip、隔离helper已移除；真实发布及UI独立验收。
- Forbidden action：不重启整机/Docker/业务/受保护18081，不挂生产数据或socket给测试容器，不在原容器执行试写，不使用接口代替真实UI恢复，不将fixture记为现场成功。
- Evidence：本计划、后续父验证原始报告/私密日志/实际c1默认prepare与guard及隔离helper生命周期证据。
