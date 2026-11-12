# 完整安装后继中的历史部分安装验收

## Goal / Current Status

ready_for_closeout。只修正本任务真实 UI 验收桥对历史 partial 的遍历。新控制包续装后，直接前代为完整 b10；更早的 partial 仍须保留身份，不能要求它是当前直接前代。真实新安装、页面和恢复均仍待单独验收，本文件不宣称其完成。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。保留既有严格字段、固定主机分工与 schema，新增祖先相邻关系拒绝条件。
- 是否从根因和长期维护角度解决：是。按已验证安装链的实际层级遍历，区分完整前代与历史部分前代。
- 是否存在临时补丁或绕过：否。没有修改 UI 操作、唯一 POST、回执落盘或产品能力。

## 经验门禁

Trigger：真实 UI 验收新的完整控制安装且更早存在 partial。Preflight check：原 UI 字节冻结、正式安装链保持、明确单元协议夹具与真实安装范围。Blocker：祖先基线、schema、主机分工或原件不符。Verification：真实旧 UI 的失败断言、当前全部相邻用例、源码前后 SHA。Forbidden action：改写历史原件、把 partial 作为完整祖先、把单元夹具冒充安装成功。Evidence：私有 released-main-ui-ancestor-tdd-r2.private.json 及对应 RED/GREEN 日志。

## BDD / TDD

Given 已认证完整前代以前有仅57已激活的 partial；When 当前完整后继被读取；Then 桥接保留 partial 并验证它的基线紧邻 v3 完整安装。错误基线、主机分工、schema 或把 partial 加入完整祖先集合，均应拒绝。

- RED：对完整保留的旧 UI 运行新增5用例，实际4失败/1通过。正向场景在 Python 桥断言失败，错误基线、主机和 schema 未抛错；重复完整祖先原本即被拒绝。日志4162B，SHA256 `426dd8aa22017572301982e5b8bd4abfb221dd40a1b559451f0a828555a2064a`。
- GREEN / REGRESSION：`SPUG_TEST_PYTHON=<已确认 Python> node --test --test-reporter=tap scripts/tests/test_main_three_target_ui*.cjs`（由载体显式展开4文件），79 PASS、0 FAIL、0 SKIP、exit0。日志12364B，SHA256 `5e3bb02f1de294f6b6398c0dc58becf76d7c7abdbecb3ba6cebffe9500f2682f`。
- 旧 UI 32371B，SHA256 `10af193fa3133ea5e8250cc628c3f93ea95b9de87c6d1a4bcd0d8ed49e1e0205`；新 UI 32892B，SHA256 `fbb8f6ae2c9b797a4e283a76b8da5f6961fabd34aff57696113d9dd0477d0894`。源码、4测试输入前后保持。无网络、服务器操作或业务 POST。
- r1 路径转义错误不算 RED；r2 实际断言已执行，外层摘要解析误按 TAP 而报错，原日志保留并从实际5项执行结果核对。当前 GREEN 在显式 TAP 下复验全部79项。
- 协议夹具仅用于单元边界；实际安装仍须完整正式 loader，实际页面仍由 Playwright 真实登录验证。
