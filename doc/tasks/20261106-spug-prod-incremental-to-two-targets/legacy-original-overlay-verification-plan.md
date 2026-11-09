# 历史原件增补的独立本地复核

## Goal and current status

in_progress。保持 108 点原冻结清单不变；独立复核 be26 服务器原视图的五份副本和引用关系，再把已核原件覆盖范围作为独立增补报告。仅本地读取已有证据，不重新读取 NAS，不执行 SQL，不修改服务器或旧清单。

## Milestones and expected verification

1. 重算既有公开报告、私密原读取 stdout、退出凭证与五份本地副本的 bytes/SHA。
2. 从原 binding 核对 point、manifest、material 的引用，再从 material 核对 expected-data；不只相信聚合结果中的布尔值。
3. 读取先前 108 点关系报告，唯一按 packageId 合并 be26 已核关系，列明剩余未知点。新报告不改变旧失败记录。
4. 对实际已取得的 typed 数据库元数据，使用固定源码的正式校验函数检查内部结构和自哈希。传入同一对象只用于内部一致性检查；不输出其等价性返回值，也不声称独立源目标数据相等、SQL 完整、应用可用或恢复成功。legacy settings 及损坏元数据不进入此分支。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。单点失败保留明确错误；不得接受重算的新指纹替代原指纹。
- 是否从根因和长期维护角度解决：是。原视图差异和元数据损坏分别归因，内部校验与实际恢复证据分开记录。
- 是否存在临时补丁或绕过：否。只读独立增补，不修改产品合同。

## 经验门禁

- Trigger：多视图历史备份原件复核。
- Preflight check：校验原报告和源码输入 pins；仅打开明确列出的已有本地证据文件。
- Blocker：原 pin 不符、引用不一致、内部正式校验失败必须逐点报告，不宣称该点可恢复。
- Verification：保存本地读回结果、覆盖数量、未知点及校验器源码 pins。
- Forbidden action：禁止改旧清单、重写旧备份、运行 SQL、用同对象比较结果宣称源目标相等、读取凭据到公开日志。
- Evidence：独立增补报告及 execution-log.md。此次本地复核不构成服务器写入或实际恢复。

## 本地校验载体 r1 前置失败

r1 在导入校验器之前因 VALIDATOR_NOT_COMMITTED_SOURCE 退出 1，未运行内部校验、未生成通过报告。独立核对三份源码 git status 均无改动；工作副本分别为 420/413/1267 个 CRLF，Git blob 为 LF，原字节 SHA 与提交字节不同。三份文件经 git hash-object --path 的标准 clean 过滤结果均与 HEAD 对应 blob 完全相同，且仅 CRLF→LF 后字节相等。r2 同时保留原始文件 pin、原冻结 pin 校验及 Git clean blob 校验，不改源码字节、不接受任意内容差异。

r2 本地聚合在未发布 9695 点缺少 expectedDataOriginalPin 时退出 1，未生成通过报告。该点此前只证明 manifest 声明与已有副本内容相同，没有原 material，不能按“原 material 的 expected-data 原件”分类。r3 保留此区别：仅该点使用冻结清单中的 manifest 声明，并重新核原本地 manifest 成员引用；不增加原 material 覆盖数量，不声称该点已发布或具备恢复准入。其余已核正文仍要求原 expectedDataOriginalPin。
