# 来源计划 HTTP 完整响应读取修复

## 当前状态

ready_for_closeout。59/58 原暂存已严格完成本地 finalization；HTTP 与传输修复的必要回归实际通过，待限定实现提交。57 的原失败保持，新的明确续办尚未派发。本子阶段未发起备份、恢复或控制服务重载。

## GREEN 与 REGRESSION 原件

- GREEN：固定 Linux 镜像中的真实 HTTP 四场景 4 PASS、零 skip、exit0（5.33秒），来源字节保持、容器已删除。`PRIVATE/source-http-native-green1.log` 98 B，SHA `b3c1142aef1737332ad6434771745b52c66573749e7de0099d635add65779d47`；公开摘要 `source-http-native-green1.json`。
- REGRESSION：父实际运行原 stager 全部非 Linux 场景与新增 HTTP/transport，共 58 PASS、8 deselected、零 skip、exit0（71.97秒）。`PRIVATE/source-http-staging-regression-r1.log` 126 B，SHA `e2cfe747582f3cedb4ae33ec457ab4ab34993b9c9ad2c30d867f95127f819822`；五个固定源码/测试 SHA 前后相等。
- REGRESSION：父在固定 Linux 镜像运行全部8个 Linux 场景及3个实际 bootstrap 环境/异常场景，11 PASS、零 skip/error、exit0；来源保持且容器删除。`control-staging-native-httpcomplete1.log` 224 B，SHA `cd3eb84205cb8b51a8021fe03e61e17cdd105897fa71059d31bc709bee58658f`，摘要同名 `.json`。
- 最终产品 stager 53180 B，SHA `b5c10c0b526a2bf94b816d357a4f68bf129ff6407da515d7f59332f0c2e3b581`；原 stager 测试 41555 B，SHA `4da522afaea47786bc3286475c3a3638c9eec6e20de623c4bceb4e1694d5d973`。原测试只补真实 HTTPResponse 协议的 length/isclosed 属性；新测试未改旧行为断言。
- 独立 activation 证据类型修复父重跑13 PASS、零 skip、exit0（6.56秒），原日志 `activation-evidence-pins-parent-green-r1.log` 101 B，SHA `d933c068923bfe506569d3e1a750f818e35d05f7c8c9f2aefd1b5bbcdcc1123d`，已单独提交 `3e51132`。59 默认完整 prepare 实际通过，不冒充远端切换。

## RED 实际结果

- 原 stager SHA256 `ef5461391a132001586c4c559f1278aa9de8d624c556672b8b31ca7b7f95568c` 保持。实际标准库 HTTPServer/urllib 四场景执行：2 FAIL、2 PASS、零跳过、exit 1（9.13 秒）。
- Content-Length 完整载荷在读完后的下一次 `socket.settimeout` 报 Windows 10038（Linux 对应原 errno 9）；不是业务失败或空场景。
- Content-Length 声明比实际载荷长 10 字节，原实现错误接受了可解析的 JSON 前缀；截断拒绝场景真实失败。连接关闭及 chunked 的正常完整响应通过。
- 原始日志 `PRIVATE/source-http-completion-red-r1.log`：3068 B，SHA256 `f0a6279db4bc4b4dc9f03a110294a91e4b9c76339a3f6f2ec4f4e414fd4d07f9`。
- 尚未修改原 stager；先完成 59/58 的冻结原件 finalization。

## 已执行边界与新增 RED

- 独立 finalizer 已单独提交 `c7a8a498b953adf72c0126a1b3c4190473cba3a6`。父实际 59、58 `--finalize` 均 exit0，生成 engine/configuration 历史 stage core，`remoteDispatched=false`、`activationPerformed=false`。
- 59 engine 1958 B / SHA `403f7e079b83ccef76804e36dcda1525264181a2efd6bb1b79cde73a4014ddd7`；configuration 7997 B / SHA `bd508710ee0a12cb3dfc3dfe757e5233d6019464c04402bfb0f1cabee5da22b1`。
- 58 engine 1970 B / SHA `a8aaedea943761cc6094bf5d0964a6e0e766ad9ad3d114c03f32f3328dc20c4b`；configuration 8262 B / SHA `771c320278fba1b4fdd59c1fda3f20d9b353eecbb493942fcc8d1a592d8c741c`。
- 真实新 dispatch 协议边界 RED：1 FAIL、2 PASS、零 skip、exit1（64.01 秒），已审唯一 SSH 收尾诊断原实现仍拒绝；未知错误及附加告警按预期拒绝。原始 `PRIVATE/stage-transport-completion-red-r1.log` 2783 B，SHA `f33ce9f301b3df6539f6ae93935123a6e3429a2b43188313368440aff3c0bfbf`。
- 两份原回执生成且所有旧 pin 已核验后，原 stager 52832 B / SHA `ef5461391a132001586c4c559f1278aa9de8d624c556672b8b31ca7b7f95568c` 按原字节独占保存到 `PRIVATE/source-http-completion-original-stager-e5f6.private.py`，再进入最小实现。原 57/r6 失败结果 SHA 保持。
- 最小实现：HTTP 在响应真正关闭后停止读取，并拒绝未满足的 Content-Length；十秒预算和大小/PID门禁保持。新 dispatch 保留原 stderr/transport 并严格接受已审单行 SSH 收尾，成功 core 绑定 transportEvidencePin；任意其它 stderr 仍失败。

## 目标与里程碑

1. 用真实 loopback HTTP 响应复现原 `fetch_source_plan` 完整读取后 `Bad file descriptor`。
2. 在保留十秒共享预算、响应上限、固定 loopback、禁止重定向、前后 PID 核验和失败暴露的前提下修复读取终止条件。
3. 真实 HTTP 协议测试及原受影响回归通过；原 57/r6 失败原件保持，实际续办另有唯一 attempt 与原失败绑定，禁止覆盖或伪造成功。

## 经验门禁

- Trigger：57/r6 candidate-before 在 fetch_source_plan 第 390 行抛出 errno 9；真实原 result SHA256 `50d2f41ca7f37dbe806a12c8cbc662353a2bb4d42a07ed84e4968bdedc8a631f`。
- Preflight check：核对原 traceback、原 stager 字节、响应实际 EOF 行为；先真实协议 RED，再最小修正。59/58 finalization 前不得改其冻结输入。
- Blocker：原件或冻结输入变化、未知终态、未完成 HTTP 响应、期限或大小超限、缺后置 PID 验证。
- Verification：以标准库真实 HTTPServer 和 urllib 请求验证 Content-Length、连接关闭与 chunked 正常完成及截断拒绝；协议用例不是服务器/E2E 业务验收。
- Forbidden action：不延长超时、不忽略任意异常、不用无连接 mock 的成功代替真实 HTTP，不重派已成功主机，不覆盖失败原件。
- Evidence：原 r6 私密 result/transport 及本任务新的 RED/GREEN 原始输出。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；依据 HTTP 响应的真实完成状态结束读取，保留完整传输与期限校验。
- 是否存在临时补丁或绕过：否。

## BDD

- Given 标准 HTTPServer 实际返回完整 Content-Length JSON，When 原函数读取，Then 完整解析、两次进程核验且不再操作关闭 socket。
- Given 连接关闭定界或 chunked 的完整 JSON，When 同一路径读取，Then 完整返回并释放连接。
- Given Content-Length 大于实际载荷，When 连接提前关闭，Then 明确拒绝，不能把可解析的 JSON 前缀当作完整响应。
- Given 新的一次明确派发真实 exit0/no-timeout、完整成功终态及唯一已审 Windows SSH 收尾行，When 原 dispatch 校验，Then 保留原 stdout/stderr/transport 并发布绑定 transportEvidencePin 的 core；任意其他 stderr 或附加警告仍拒绝。此规则与已审 finalizer 一致，仅作用于新派发，不追改旧失败。

## 57 原失败后的明确续办边界

59/58 原 finalization 完成后，修正共享 stager；原 57/r6 失败及其旧源码先保存原字节、记录 pin。新一轮重新运行正式 prepare，追加原失败、传输、attempt 和旧源码证据 pins，再由既有 `dispatch_prepared(task, journal, prepared)` 使用全新、独占、持久的 journal 子目录保存本次 attempt。计划、远端路径和公有输出仍绑定原 r6，原目录及失败不能改写；不允许自动重试或未知/部分写入续办。远端仍从原物理锁开始重复全部实时准入、路径不存在及写后保全检查；只对确认写前失败的正式服派发。
