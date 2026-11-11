# 原请求派生owner自动登记

## Current Status

implementation_verified；实际来源控制安装与真实Spug计划验证待完成，不宣称整体任务完成。

## 目标与设计约束检查

保留resolve生成的不可变请求配置合同，使无人查询的已成功增量在下一次计划中自动登记。只验证原配置、request-inputs、原父点绑定及允许的parentChains/来源capture路径派生，不重新resolve或读取后来的程序代次。不引入fallback、吞异常或临时绕过；从合同根因解决并保留worker、epoch、材料和原件验证。

## BDD与TDD

- Given 真实Linux launcher退出2、独立worker成功退出且I1未登记；When 新控制进程构建计划；Then 验证原请求派生owner并自动登记I1，父链选择I1/FULL，原completion/result不变且queries不存在。
- Given 原请求、模板pin、父绑定、父引用/点、capture路径、其它owner字段或inputs字段改变；When 构建计划；Then BLOCKED且三个登记均不存在。operationRoot错配在更早原owner准入阶段拒绝；缺inputs也禁止部分发布。
- RED实际12项：正向复现SOURCE_POINT_OWNER_BINDING_INVALID；另1项测试误要求更晚错误码，修正为实际更早ORIGINAL_OWNER_ADMISSION_NOT_FOUND，原件保留。
- GREEN实际12项全部通过，但外围错误要求加载此次未运行的boundaries测试模块，故该载体仍记录FAILED。
- REGRESSION：原83+新12共95项实际Linux PASS/0FAIL/ERROR/SKIP，native0，输入SHA前后保持，容器已删除；原预算180/300秒不变。证据PRIVATE/request-owner-regression-r1-attempt/verification-result.private.json，完整stdout/stderr/JUnit均保留。

## 交付与收尾

专用worktree C:/Spug/runtime/private/u-src-r5，起点实际已安装ddba4c698db509ebd1a299ff8d0a9c70e50c8a42；验证后只提交Native及两个协议测试和本记录。随后仅用目标提交的clean输入运行官方build_variants，并核两个包全部成员SHA/compile及实际STANDARD差异仅Native。新提交待合回任务及int_main，未清理worktree；安装前另记实际准入，保持target、业务、挂载、epoch、I1原件，不派重复备份。
