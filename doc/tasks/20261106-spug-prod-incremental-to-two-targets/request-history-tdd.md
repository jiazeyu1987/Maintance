# 历史请求与共享模板生命周期

## Current Status

implementation_verified；实际安装、真实Spug计划与收尾待完成。

## 目标与设计约束检查

已完成捕获以原冻结请求owner及原生成功结果为准。共享capture/objects模板可合法升级，其旧pin仅记录当时身份；它们不参与owner的两项派生，不在历史调度阶段回读活模板来判旧请求失败。请求inputs、原模板owner、父绑定、冻结repository及epoch证据仍严格校验并在发布前后复核。fallback/降级/吞异常=否；从正式配置生命周期根因解决=是；临时补丁=否。

## BDD与TDD

Given 已闭合请求自身原件保持，capture模板、objects模板或两者升级；When 新进程构建增量计划；Then I1自动登记并被选择，原inputs/frozen capture/completion/result不变，queries不存在。原请求和owner等既有错配场景仍全部阻断。

RED：三种升级场景实际均NATIVE_PIN_CHANGED失败，原12项通过，0ERROR/SKIP，native1；原件保持、隔离容器删除。载体另严格拒绝本次未加载的boundaries模块，不误记PASS。最小实现只将两个共享模板输入改为pin结构验证，原其它校验保持。

GREEN/REGRESSION：原95+新3共98项真实Linux PASS，native0，0FAIL/ERROR/SKIP，实际全部模块来源与SHA验证通过，输入保持且容器删除，原180/300秒预算保持。证据PRIVATE/request-history-regression-r1-attempt/verification-result.private.json；完整stdout/stderr/JUnit保留。

## 发布与收尾

本轮新专用worktree C:/Spug/runtime/private/u-src-r6，起点实际019f4623574e2d9bc4c7f4857f94709bb94c1b5d，验证后只提交Native、新增三个场景及本记录。官方双包仅用该提交clean输入构建，STANDARD实际差异只允许Native。安装按原授权仅重启57来源控制服务；不改业务/target/NAS/epoch/旧点，不派新备份。待合回任务与int_main并在合并结果验证后删除，当前保留。
