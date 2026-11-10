# 44 个旧设置点的本机前置事实核对

## Current Status

completed（有限本机事实清单完成，未实施/登记/放行）。此前补充合同设计 SHA 保持冻结；本阶段没有运行 SQL、Docker、NAS、远端或测试。

## 目标、里程碑与验证

- 核原 108 点映射中 44 个旧设置候选的 setting/material/binding 与完整前缀身份。
- 只读已显式列出的本机小元数据，区分 SQL/程序载荷只有原 pin、本机独立副本可用及版本 schema 依据缺失。
- 输出逐点事实报告、首个可继续验证的正例候选及确切阻断依据；不能把候选称已兼容/可恢复。
- 验证输出 44 个唯一 ID、每个事实的输入原件路径/pin，以及原 map、reconciliation、设计 SHA 保持。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；未知或缺件逐点记录，不猜表数/兼容性。
- 是否从根因和长期维护角度解决：是；只增加有原件出处的逐点前置清单，供后续有限验证使用。
- 是否存在临时补丁或绕过：否；不改任何旧证据、产品、测试、登记或运行环境。

## 经验门禁

- Trigger：旧设置点需要独立 SQL 回放参考之前，先核逐点原件与兼容依据。
- Preflight check：复用已核 155 个本机读回原件；按 map/report 显式路径读取小元数据，不重复 NAS/完整载荷 SHA。
- Blocker：原件引用不符、缺 binding/前缀、只有远端 payload pin、缺该程序版本的明确 schema 要求，分别记录，不连坐同组其它点。
- Verification：只验证元数据身份/本机副本可用性和清单闭包；不运行 SQL/测试/业务，不把 metadata 通过说成恢复通过。
- Forbidden action：不扫描 PRIVATE/归档、不读 SQL 正文或大载荷、不 Docker/NAS/远端、不改 frozen map/设计 SHA，不推测 3 表或 15 表。
- Evidence：原冻结 map、新 reconciliation、父已核读回报告、显式 program 材料；承接 `docs/release-agent-checklist.md` 的完整读回/实际封包/保留失败门禁。

## 执行记录

- BDD：Given 44 个显式旧设置点及现有小元数据，When 只读核本机原件/前缀/载荷引用，Then 每点输出事实、未知及独立阻断，无恢复或兼容通过声明。
- 本阶段为只读评估与报告，不进入实现 RED/GREEN。
- 只读命令统一为 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 -`，显式解析 map/readback/program 报告引用的 UTF-8 JSON。小元数据按原 bytes/SHA 核等；不枚举目录、不打开 SQL/tar，不做大载荷 SHA。
- 中途统计输出 helper 曾 exit 1：`json.dumps(Counter(tuple-key))` 拒绝 tuple 键；当时未写报告、未调用外部环境。改为字符串统计键后 exit 0。这是本机报告序列化错误，不是备份原件或恢复失败。
- 正式事实构造命令 exit 0 / 7.295 秒：44 唯一点，16 FULL、28 INCREMENTAL；43 点原 setting/material/binding 身份及完整前缀位置核等，0 failedChecks。该 43 点的前缀唯一集合也是这 43 点，未跨入 reconciliation 的 4 个正文失败点。
- 本轮实际读取 191 个明确 pin 的本机元数据文件，共 33,431,880 B，包含旧设置小正文的内容核对；没有读取 SQL/tar 或访问 NAS。不是复验全部 155 原件，也不宣称执行了完整 SAFE 载荷准入。
- 独立结果断言命令 exit 0 / 0.197 秒：44 个 ID 与 frozen map 的旧设置集合完全相等；43 个前缀通过；全部 MAIN 兼容/本报告准入均为 false；原 map/reconciliation/设计的 bytes/SHA 均保持。

## 结果与可行动边界

- `legacy-settings-local-prerequisites-20261111-r1.json` 为逐点事实清单，每点含原 setting/material/binding pin、完整前缀核对、SQL/程序的远端原 pin、本机副本引用状态、版本 schema 依据及独立缺件码。`REMOTE_PIN_ONLY` 仅说明这些显式记录未提供本机副本，不表示归档不存在/损坏，也不要求为产品恢复重复下载现有远端载荷。
- 43 点有原 material 且旧 setting 与其 expectedDataPin 内容及路径引用匹配。`smallapp-9695bf3fb95d4ec4a19eb6fbe6329066` 虽有相同内容的旧 setting 副本和 manifest SQL 声明，但缺原 point/binding/material/完整前缀，不能补签或用另一点副本恢复其绑定。
- 44 点均未在本轮明确引用的原件中找到本机 SQL/tar 独立副本或该归档程序版本的必需 schema 合同；这是限定输入范围内的未知，不是全盘“文件不存在”。不据 `rehearsal`、同组、表数或当前 MAIN 版本推断历史版本兼容性。
- 完整可执行正例数为 0。优先 MAIN 正向候选为 `smallapp-811ed843c29c4040be1de5bcb87258e7`：FULL 单点、旧业务库 setting/material 闭包、已有原五角色 tar 全验和三目标 metadata 绑定。尚缺明确可供隔离回放的 6,428,017,136 B 原 SQL 与该归档程序精确 schema 要求；既有远端 tar 全验不因没有本机 tar 副本而失效。
- 最小 SQL 参考实验候选为 `smallapp-e774fa9f6f544aea8d3cbc9208d05938`：FULL 单点，原 SQL 声明 1552 B。它不是 MAIN 正例，也未证明 3 表或其它表数；当前仍只有原 SQL pin，未执行或采集载荷。
- 后续只先解决所选候选的明确原件/版本结构要求，再经父审进入隔离实际 SQL 参考及 BDD/TDD；未请求重复 NAS、未登记或放行任何点。本机事实通过不能替代 SQL 重放、程序兼容、目标运行及业务验收。

## 冻结输入

- 原 108 map：921197 B / `96a43267c5409cf2f277f4f5e21570f5c83442aa8b5a2201f243f5aabc9a86e4`。
- 新 reconciliation：149203 B / `fa1c1f745630ef45ab55a9f7f31e50c9ed7ad092fa71b761bd2bc1e16d63d888`。
- 补充合同设计：15620 B / `84b0ff64f9ab344a58562952687e0996c3ba7226d62940ae5bbd446724cc4eed`。
- 本阶段事实报告最终：438026 B / `7ef801925b56ad841cd9c413e4dd0083cf826919472ca23d2e15149a9815fac2`。最终有限断言 exit 0：44 唯一 ID、43 个身份/前缀通过、三个冻结输入未变，UTF-8 无 BOM；没有大载荷 SHA/SQL/tar/网络动作。
