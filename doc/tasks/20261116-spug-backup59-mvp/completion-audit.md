# 备份服 MVP 验收与收尾审计

## Current Status
completed

## 已验收结果

| 项目 | FULL | FULL + I1 + I2 |
| --- | --- | --- |
| Spug原任务 | smallapp-80eac03c768c47268e65141e22ad1468 | smallapp-f0c503e401204fd0a2d263937e1d3b13 |
| 原任务终态 | SUCCEEDED | SUCCEEDED |
| 11表基线计数 | 全部匹配 | 全部匹配I2 |
| 真实登录及用户页 | PASS | PASS |
| 三附件真实页面字节/SHA | 3/3 PASS | 3/3 PASS |
| 实际业务写入 | 0 | 0 |

I2最终差异表：erp_kingdee_sync_run480、infra_job_log87458、dcc_registration_certificate_daily_run72。其余8个验收表保持基线。I1/I2附件新增/修改/删除均为0，本次证明附件保留，不声称覆盖非空附件增删改；未进行全库逐行内容摘要核验。工作台context写请求每次验收均阻断1次，未列只读白名单。

公开计数及四份页面摘要随本目录保存；详细附件hash、私密原生证据、凭据保留私密目录，不进入Git。临时SSH验收隧道PID32632已由父精确停止，18089无监听；.59恢复后服务与Spug保留。

## 最终融合保护方案

- int_main基线25fe7ed，精确final-integration基此提交迁入本任务增量；没有整支旧integration融合。
- 已核主线1699项既有dirty/untracked，仅docs/request-command-log.md与本任务路径重叠且未暂存。先持久保存该文件原字节/SHA与binary patch，在final结果临时副本验证可应用；仅该文件短窗口恢复HEAD，ff-only融合后恢复原补丁。其余文件不暂存、不重置、不stash。
- 已有定向证据：Spug46、JS82、Linux12、计数2，后续数据库4、健康5/native28全部PASS。融合后仅核固定树/任务文件和必要轻量语法，不重跑已通过矩阵。
- 独立实现Agent只读审查PASS，无实质阻塞；已核共用宿主锁、精确终态重置、prepared未全库等价字段及实际健康probe。final-native-audit.md证实原生SUCCEEDED/exit0、FULL→I1→I2顺序、保护路径保留、暂存清理和预约自动释放。已ff-only融合fd0b45d、完成最小结果验证及13个release/final-integration清理；本次单独提交completed记录，详见closeout.md。

## 自有工作区清理范围

仅本任务ROOT/local-install下release-worktree及release-v2至release-v13，共13个，均已核clean、HEAD固定发布输入、无新提交；逐路径Git删除exit0及不存在结果已记录于closeout.md。确认本任务发布载体无消费者后执行git worktree remove，不使用强制删除。

final-integration已合主线且clean并完成必要验证后，从其它cwd执行git worktree remove，最终记录在主线仅精确暂存任务文件。原integration工作区和branch保留以恢复未迁入的部署基线历史；父managed受保护工作区保留，不绕过app保护。无关并发任务工作区/进程不动。
