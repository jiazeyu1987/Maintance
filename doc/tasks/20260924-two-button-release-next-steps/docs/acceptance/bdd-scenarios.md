# 两入口发布行为场景

## Purpose and Scope
覆盖两个主要入口、固定后台编排和安全门禁。以下为计划场景，尚未执行。

## Evidence Reviewed
用户已确认范围、implementation-plan.md、R22冻结代码、现有Orchestrator/Store/Scheduler、前端四阶段入口和生产锁SQL。

## Feature Scenarios
| ID | Given | When | Then |
| --- | --- | --- | --- |
| AC01 | 批准版本和依赖齐备 | 点击发布测试服一次 | 固定源和隔离输入，后台完成构建、校验、部署至TEST_DEPLOYED |
| AC02 | 新工作流以测试部署为目标且构建READY | 浏览器已关闭 | 后台自动继续，无需第二次页面部署请求 |
| AC03 | TEST_DEPLOYED且真实证据/恢复候选有效 | 晋级弹窗明确确认验收 | 复用acceptTest形成TESTED，绑定同一测试operation和双摘要 |
| AC04 | TESTED且正式预览合格 | 用户确认晋级 | 用一次性grant部署测试过的原包，禁止重新构建 |

## Failure Scenarios
| ID | Given | When | Then |
| --- | --- | --- | --- |
| AC05 | 构建/包校验失败 | 后台收束 | 不部署测试服，保留实际失败阶段与证据 |
| AC06 | 无锁、旧终态行或他人RUNNING行 | 执行生产获取锁SQL | 首次/终态重获正确绑定新lease/fence；他人活动锁拒绝；失权后零业务写入 |
| AC07 | 操作已派发且写入结果不明 | 断线或进程中断 | 保持隔离，不当作零写入释放锁或自动重试 |
| AC08 | 缺测试结论或有效恢复候选 | 点击晋级 | 不形成TESTED、grant或生产operation，页面展示原因 |
| AC09 | 提交、执行器SHA、包摘要或目标变化 | 预览/执行 | 原证据失效并阻断，不改摘要补绿 |
| AC10 | 正式迁移/部署失败 | 收到失败 | 保留恢复责任，不默认成功、不执行未批准数据回滚 |

## Boundary Scenarios
| ID | Given | When | Then |
| --- | --- | --- | --- |
| AC11 | 相同请求身份 | 双击/网络重试/两个推进者 | 一个workflow，每阶段一个有效operation，无重复写入 |
| AC12 | 构建完成或派发临界点 | 控制台重启 | 据持久证据恢复，未确认结果则阻断，不猜测重跑 |
| AC13 | 历史READY/FAILED缺少新执行目标 | 新scheduler启动 | 不自动部署历史记录或沿用失败tag |
| AC14 | 确认取消、grant过期或stateVersion变化 | 再次提交 | 不发布，不把取消当测试失败，不复用grant |
| AC15 | 两次明确新请求来自不同批准提交 | 发布原因相同 | 与网络重试区分，冻结正确版本，不错误去重 |
| AC16 | 中文输出或敏感配置 | 写日志/错误结果 | UTF-8可读、敏感值脱敏，页面/workflow/operation一致 |

## Open Questions
产品选择已明确：两个主要入口，真实验收放入晋级弹窗。新增持久字段的具体序列化方式在M0基线确定后选定；缺字段不能推断为自动发布授权。

## Test Blockers
缺隔离MySQL、固定浏览器、真实账号、批准源或独立GO时停止对应验证，未执行不能写PASS。
