# 原381操作配置物化关系 TDD

## Current Status

ready_for_closeout。本机实现及必要验证已完成，实际全链/原UI由父继续。本项无SSH、业务POST、恢复或提交。

## BDD

- Given旧base owner与真实operation owner因正式ArchiveRestoreOwner/v1物化不同，When没有显式typed证据，Then原FAILURE_REQUEST_CONFIGURATION继续拒绝。
- Given58/原381/source57/I2实际产品只读PASS、精确27metadata原字节和actualACTIVATE，When明确提供context，Then仅重建产品最后projection、全文canonical比较，旧失败/配置/所有其它sources保留。
- Given其它source、deadline、target、point、binding、未知配置字段、profile或请求scope漂移，When核验，Then拒绝；不能用PASS布尔或删sources比较代替。
- Given实际collector stdout完成但OpenSSH关闭通知、exit未落盘，When独立finalize，Then原carrier仍FAILED、exitCode=null、通知原字节保留，本机重算配置关系通过；不重SSH、不捏造exit0。

## RED → GREEN → REGRESSION

- RED：PRIVATE/archive-owner-continuation-red-r1.xml，13 FAIL/1 PASS，缺新typed参数与模块；默认旧相等场景仍PASS。
- GREEN：PRIVATE/archive-owner-continuation-green-r1.xml，14 PASS/0 skip，2.55秒。
- 最终GREEN：PRIVATE/archive-owner-continuation-green-r2.xml，19 PASS/0 skip，3.83秒，含真实API配置判定全流程和拒绝假exit0/错误profile/pin。
- 相邻回归：PRIVATE/archive-owner-continuation-adjacent-r1.xml，97 PASS/0 skip，31.47秒，只跑原partial_native/repeat两文件。未扩大完整历史回归。
- 回归包装失败保留：PRIVATE/archive-owner-continuation-regression-r1.xml混合PRIVATE和repo路径触发C盘共同root、Documents and Settings PermissionError，0业务用例执行。拆成同范围两个命令后获得19+97实际PASS。
- 原件保存：successor83043B SHA803bfbd0db121c1668368a6e2c12beffbbde9676ba87ec26dac77ade6d41f2a8先独占snapshot并逐字节确认；原planning及所有安装回执不改。
- 已运行finalizer：2135B context SHA72fd2edf6b23d287b314b3962701e82b3417d30e569d18bb950c7560c5bb0078，27原件、exitCode=null、原carrier FAILED、0写/0载荷。
- 新verify的inputs()已真实本机通过；未运行main、未生成selection。父以原SourceRoles/v1 r2 custody运行完整loader，随后原UI消费。
