# 当前数据库契约版本发布测试服
## Current Status
completed
## 目标
以最新已提交 IntRuoyi int_main 构建新版本并仅发布测试58；验证数据库契约、运行版本、健康及真实页面。前序数据库契约任务已完成；旧正式发布任务保留业务基线阻塞，不执行晋级。
## 里程碑
1. 读取发布规则，确认最新提交及任务锁，创建本次临时worktree。
2. build-release -> publish-test，同一新releaseTag。
3. 运行态、页面、版本及说明验证，记录并清理本任务worktree。
## 预期验证
operation SUCCESS、manifest、IMAGE_TAG、双镜像、backend UP、frontend 200、真实登录及版本说明；当前数据库契约各阶段回执。
## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，使用已交付当前契约。
- 是否存在临时补丁或绕过：否。
## 经验门禁
- Trigger：测试服发布与临时worktree。
- Preflight check：固定已提交源码、新临时目录、已安装执行器、任务锁、恢复依据、不可变契约清单。
- Blocker：源码身份不明、活动任务冲突、契约失败、运行态不一致、页面必要功能失败。
- Verification：同tag构建测试发布、契约回执、运行态及真实页面；完成后归属清理。
- Forbidden action：不发布正式或审查服、不mark-tested、不重放旧SQL、不拼接tag、不混入脏改动、不把基础冒烟当订单业务验收。
- Evidence：execution-log.md及发布回执。

## 已完成
构建、测试发布、三阶段契约、实际运行态和真实页面全部完成。应用构建worktree无新提交已自动删除；维护worktree已核5291文件并删除，登记与物理目录均不存在。详见release-result.json与acceptance.md。
