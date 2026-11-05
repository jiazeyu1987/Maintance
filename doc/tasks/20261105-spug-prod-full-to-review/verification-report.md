# 正式 FULL 经 Spug 恢复到备份服验收

## 当前结论
completed。History359 / `smallapp-a63174ccdf0c42f187f182e172653759` 于北京时间2026-11-06 02:34:41（UTC18:34:41.896554）原生 `SUCCEEDED`、实际 exit0。数据库、附件、引用、受控Redis、原服务健康、恢复后真实登录及业务列表均通过；最终归档校验、暂存清理及预约释放通过。正式来源与196个其它业务容器原运行态保持。此结论仅覆盖本次正式FULL到原.59 MAIN；不替代.57目的地登记验收。

## 精确范围
- 来源：正式服务器 `172.30.30.57`，`intruoyi-57-safe-20261024-v1`。
- 独立完整 FULL：History350 / `smallapp-73cd541a95d84d6a86f9d693e4053c75`，14378 文件、26090562595 字节。
- 共同恢复点：`sha256:e94ad09d511f2b9ebb576e8b8f460a04087ddfbf3d2ed92b6391bb658b59d3c4`。
- 目的地：备份服（现行文档称审查服）`172.30.30.59`，`intruoyi-main-59-safe-restore-20261104-v1` 原 MAIN，覆盖记录、附件及登记 Redis DB。
- 第四次真实浏览器登录 Spug、选择精确 FULL 与 .59、确认覆盖后仅最终 POST 一次，HTTP202；沿同一原进程观察至原生成功，没有再次 POST。前三次真实失败及正式准许链原样保留，不将整段排障描述为第一次就成功。

## 已修复和保全
| 原操作 | 真实失败 | 正式修复 | 原记录保护 |
| --- | --- | --- | --- |
| History356 | `ARCHIVE_LEASE_FD_BUDGET_EXCEEDED`，原 exit1，写入前失败 | 仅本任务控制服务持久 `LimitNOFILE=65536`，原及当前恢复子进程实测继承；追加显式写入前失败准许合同 | FAILED_RETAINED、原 28 pins、原 UI 回执 SHA 保持 |
| History357 | `RESTORE_FILENOTFOUNDERROR`，MAIN 误租赁未使用的演练 iptables；原 exit1，写入前失败 | MAIN 仅租赁实际使用的 Docker 可执行依赖；演练仍必须租赁 iptables，归档和请求租赁及哈希守护保留 | FAILED_RETAINED、另 28 pins、原 UI 回执 SHA 保持 |
| History358 | `MAIN_SERVICE_NETWORK_CHANGED`，前端默认bridge动态IP随停止正常清空却被误判；原exit1，清空后失败 | 正式验证动态附加网络生命周期；固定业务端点、原HostConfig发布端口、网络身份和真实Docker成员继续严格绑定 | FAILED_RETAINED、另147 pins及原UI回执保持；原UUID/0表、三writer停写 |

前两次失败均由原生明确证明无目标写入、无 intent/importer，严格原运行态、UUID、885 表和全部业务基线核验通过后，才由正式 CLI 追加同来源/同点/同目标v2一次性准许。第三次已写入，修复后严格观察原UUID/0表/三writer停止/203失败pins并通过，使用正式v1写入后准许及其资源释放回执。未修改失败历史或删 claim。

## 代码和构建验证
- `aab0b3f7bcb93b1cf144793c271df15bbae2c0f9`：写入前失败显式准许，BDD/TDD 实际 Linux RED/GREEN；行为合同 206 passed，实际 SAFE/FAST 封包 15 passed。
- `288d4c39f435592cf4bb5bebfa54a8063dbdecf4`：MAIN 按真实执行依赖租赁，实际 SAFE 构造代码 RED 复现、GREEN 通过，相关回归 86 passed。无 skip 或 mock 成功。
- `76bb60bd1fe7bc0c5ee771483b02d6c29e8fcf10`及`f819fbedd4dbd389044560d54b215f99a4d59f81`：动态附加网络与固定宿主发布地址生命周期，实际Linux RED/GREEN及最终157项相关回归通过。首候选被真实目标校验拒绝并未激活，补齐精确宿主地址用例后新提交独立构建，真实停写目标校验通过才启用。
- 测试载体缺 Git 元数据与子进程依赖导致的原 ERROR/FAIL 日志保留；修正真实测试环境后复验通过，不把环境故障写成产品测试通过。
- 四次分别从精确已提交内容、新建专属干净临时发布 worktree 构建，未包含开发脏内容。各122文件SHA与编译验证通过，只更新自有控制代次，目标/来源合同不变。
- 四个专属发布worktree均无新增提交、不需合并，正常删除后核实体与Git注册均不存在；本任务三个专用测试容器/卷均按归属正常清理，证明在本目录。
- 当前控制引擎为`engine-retry-f819fbed`，稳定服务器路径，不依赖临时发布worktree。原开发工作区因三服登记任务未收口而保留，未删除其它任务资源。

## 最终真实验证

| 验证项 | 结果与证据 |
| --- | --- |
| 原生终态 | `restored-native-evidence.json`：同一History359、同一FULL与目标，SUCCEEDED/实际exit0，15个结果文档pins严格核验 |
| 数据库 | 885表、512156行，完整结构和数据独立等价；原UUID `a4f03708-cc74-11f1-9cce-0242ac1def16` 保持 |
| 附件与引用 | 5916版本、4920唯一内容、9653189892字节，原版本身份和物理内容读回一致、deleteMarker0；所有引用与不变量通过、缺失0 |
| Redis | 来源登记DB1快照0键，恢复/独立验证0键；不宣称非空值或TTL样本已实测 |
| 原服务 | `restored-runtime.json`：五个原容器/镜像运行，MySQL与Redis原PID/启动时间保持，后端UP、前端HTTP200 |
| 真实业务页面 | `target-review-after-restore-business.json`：恢复完成后实际Chrome登录→系统管理→用户管理，2117条/20行，版本2026-11-03-12-15-42，与恢复前基线一致；业务写入0 |
| 来源保护 | `source-preservation-verification.json`：终态后核.57五个原容器/镜像/PID/启动时间保持，后端UP/前端200 |
| 无关业务及失败记录 | `preservation-verification.json`：196个其它业务容器原运行态保持，203远端失败pins保持，完整356→357→358→359一次性准许消费链成立 |
| 归档与清理 | 原共享归档只读、完整FULL保持；恢复暂存按正式清理回执删除，宿主资源预约已释放，未清理失败材料或共享NAS |
| 运行与发布收尾 | `closeout-verification.json`：四个专属发布worktree实体/Git登记均不存在，三组自有测试容器/卷无残留，原控制active/enabled和稳定运行路径通过；28份本地原失败材料逐字节SHA保持 |

四次实现已独立提交。最终记录编码、语法、27个已知私密值扫描与diff检查通过，按本任务目录和请求日志限定暂存后单独提交；本任务局部.gitattributes禁用换行转换，提交前逐文件核暂存blob与原字节一致。不包含私密原始材料、Python缓存或其它任务文件。原三服登记开发worktree因另一目的地合同仍阻塞而保留，不自动合并int_main或删除其它任务资源。
