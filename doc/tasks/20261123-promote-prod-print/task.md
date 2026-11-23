# 正式服发布并包含打印助手

## Current Status
completed

## 目标及授权
用户明确要求发布正式服务器，也包括打印助手。以已测试同包2026-11-23-22-02-22 / 275c870118f8096328d94bd38700455de3e76fc0为候选，先核实际版本与助手交付合同，再执行正式晋级和真实只读验收。前序20261123-update-test-release已completed。不得把主程序镜像发布等同于独立助手已发布。

## 里程碑
1. 已完成：原包tested及正式只读预检通过；助手身份/配置和旧容器恢复依据已保留。
2. 已完成：隔离工作区624f6de；正式打印URL已登记且稳定执行器重载通过；助手不可变镜像晋级通过。主程序JOB-0ee3f179cb及开放JOB-b530c70f8e均succeeded。
3. 已完成：独立运行态PASS；维护38084和公开8081入口真实登录、菜单/版本、打印认证均PASS_WITH_OBSERVATIONS，范围见page-acceptance.md。
4. 已完成：发布结论已记录；自有worktree清理PASS（无新提交、Git登记及实体目录均已删除）；稳定执行器40124仍在原source路径，配置摘要保持。最终任务记录单独提交。

## 预期验证
同一releaseTag及包摘要贯穿晋级；operation SUCCESS、manifest、IMAGE_TAG、实际镜像、backend UP、frontend 200全部一致。助手实际镜像/部署来源、正式公开地址和内部验票地址正确，Playwright真实登录后从现有入口进入助手成功；不作正式业务数据测试写入。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，复用正式晋级和助手交付合同。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：正式发布和打印助手部署。Preflight check：先读发布/访问/登录/工作区文档，核同包验收、锁、真实目标与独立助手合同。
- Blocker：包身份或迁移合同不符、助手来源不可追溯、缺恢复依据、必要页面不可用或未知异常。
- Verification：独立运行态、真实页面与助手认证、清理回执和稳定路径。
- Forbidden action：不重编已验包、不拼接releaseTag、不拷贝测试租户业务数据/凭据到正式、不删除/mnt/nas、不改历史失败为成功。
- Evidence：本任务execution-log、脱敏验收报告及外置私密原始记录。每次高风险动作前记录experience-preflight PASS；收口先ready_for_closeout后completed。
