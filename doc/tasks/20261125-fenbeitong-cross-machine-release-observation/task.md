# 核对另一台机器发布的分贝通

## 目标与授权

用户询问另一台机器已将分贝通发布测试服及正式服，本机能否看到。只读核对本机控制台记录、远端实际运行身份及可取得的发布凭据，区分真实运行态与本机未知历史。不触发发布、重启、同步或业务写入。
前序自有任务20261124-bounded-service-recovery已completed。

## Current Status

completed

## 里程碑

- [x] 建立任务文档并读取经验索引/PowerShell门禁。
- [x] 按多机器发布接管门禁确认访问入口、目标和私密配置来源。
- [x] 只读核对测试与正式分贝通运行版本/健康与发布证据。
- [x] 保存脱敏结果，完成记录并回复可见性及限制。

## 最终结果

- 采集时间：2026-11-25T09:32:14Z（America/New_York为2026-11-25 04:32）。两个目标观察期间容器ID、镜像和启动时间稳定。
- 测试172.30.30.58：2026-11-25-16-50-01，running，HTTP200/success=true/status=ok；部署回执JOB-fccf5f1839、验证回执JOB-cba63fd7b2均succeeded/complete并绑定当前容器。
- 正式172.30.30.57：同版同镜像同包，running且相同健康结果；部署JOB-c9131deb67、验证JOB-4413e71479均succeeded/complete并绑定当前容器。
- 两服imageId=sha256:fd3abf301f72f780eafc35c3fd9f5893ab5c173dfe37ccf217eb0912dbccb880；packageSha256=79fe21eab8045c21c5e3f5cec9b490edfc1572d7e0946415e6cc48c9caf3b428；manifest与内置源码摘要一致。
- 可见性：本机可独立只读取得服务器实际发布结果，无需重导包。本次不导入另一台电脑本地任务或业务验收历史，不宣称完整业务验收、原tar全量SHA或恢复完整性已验证。
- 无应用代码变更、无worktree/控制台/远端文件创建或业务写入；仅任务证据及共享请求记录精确提交。analyze.py从真实证据校验两服身份、manifest、健康与原回执均PASS。

## 预期验证

真实只读观察，不用本机记录缺失推断远端未发布；不把主应用版本误当分贝通版本。需要时读取远端manifest/operation/IMAGE_TAG/实际镜像与健康，无法取得的历史明确未知。

Given另一台机器发布独立分贝通助手，When只读远端标签、内置release-info、镜像、manifest和原部署回执，Then以一致身份确认当前已安装版本，不伪造本机发布历史。Given健康接口正常，Then只确认技术健康，不冒充报销或第三方业务验收。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；依据权威远端运行态及跨机器门禁。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- Trigger：多机器发布结果核对、测试/正式只读状态及中文PowerShell。
- Preflight check：读取server-access及release-agent-checklist多机器门禁，确认分贝通目标与已验证本机配置；凭据只在内存使用，输出白名单字段。
- Blocker：目标/配置/访问身份不明、无只读观察入口或凭据不可用时阻断相应结论；不猜测服务器路径。
- Verification：逐环境记录实际版本/身份/健康与本机历史可见性，保留脱敏证据、命令意图及退出状态。
- Forbidden action：不重新导包、不伪造历史、不覆盖私密资料、不修改或重启远端、不发送消息或调用分贝通业务同步。
- Evidence：本任务execution-log与脱敏观察JSON；经验索引命中docs/release-agent-checklist.md多机器发布接管门禁、docs/server-access.md和docs/powershell-memory.md。
