# be26原件服务器视图只读核验

## Current Status

in_progress。旧Windows UNC目录的四份repository元数据读取FileNotFoundError；此前真实正式服程序完整读回报告已绑定同一四个原pin。为区分视图缺失与原件缺失，按用户已允许三服只读核查范围，只读172.30.30.57的四个确切原路径。

## Scope and verification

- 输入严格固定historical-program-archive-57-be26b59-r1.json列出的point、manifest、binding、material原pin，合计20179120字节；不读images配置、tar、SQL或附件。
- 四份都核等后，按真实material.database.expectedDataPin与manifest完整pin或唯一等内容成员关系，至多读取一个数据库证据JSON。总上限5对象/36MiB，单文件16MiB；服务器原生60秒、宿主120秒。
- 仅SSH只读，操作nonce与真实PID/startTicks/argv写本机私密原件。宿主观察失败时先查同一原进程，不重复派发，不按SSH退出推定远端终态。
- 每份源文件读取前后stat/fstat、普通文件/链接/大小及内容SHA核等，副本只写本机新PRIVATE目录；原状态及缺失报告保留。若仍缺文件，不换路径搜索或生成替代数据。
- 公开仅记录实际文件数、原pin、格式/关系和失败码，绝不记录业务内容、密钥或连接串。成功仅证明原字节可读，不证明业务恢复。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。显式验证另一已受验物理视图，任何失败保留，不改变原pin。
- 是否从根因和长期维护角度解决：是。查清目录视图差异及原件可用性。
- 是否存在临时补丁或绕过：否。

## 经验门禁

Trigger：Windows旧UNC视图缺失、服务器近期受验原pin存在。Preflight check：已重读映射server-access及release-backup-restore，目标57、固定SSH身份/host key和Python、确切5对象/预算。Blocker：身份/原pin/路径/预算错配或原进程未知。Verification：原生退出、原PID实际不在、每份字节SHA和独占副本；不借此宣称恢复成功。Forbidden action：不写服务器/NAS、不改mount/fstab、不调用控制选择接口、不操作业务/锁、不读大载荷。Evidence：历史程序原件报告与本轮独占read intent/program/终态。
