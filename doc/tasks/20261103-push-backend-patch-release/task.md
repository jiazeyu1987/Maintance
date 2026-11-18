# 提交并推送后端补丁及全量发布代码

## Current Status
completed

## 目标与授权
用户要求“提交推送代码”。核对本任务维护仓及IntRuoyi源码仓的实现与收尾提交，提交本任务尚未提交的相关文件，推送到各自任务分支并核对远端提交。沿用此前不自动合并int_main的边界；保护其他任务或用户改动。不启动发布或修改服务器。

## 里程碑与预期验证
1. 识别仓库、适用指令、分支、未提交改动及已有验证证据。
2. 核对远端分支与本任务提交范围，检查敏感信息和大对象；仅提交本任务文件。
3. 正常推送任务分支，不强制推送，核对远端HEAD与本地一致。
4. 记录结果并提交推送最终任务记录。

## 当前进度
1. 上轮发布及耗时记录均completed。维护仓为codex/spug-backend-jar-patch-20261102，IntRuoyi为codex/backend-patch-full-validation-20261102；两处原工作区均干净，仅新增本次推送记录。
2. 已通过本机7890代理正常fetch；维护仓25个、源码仓6个提交未在origin存在。前者包括本线程清理与补丁实现及收尾，后者包括启动日志、DCC/展厅/Quartz修复及收尾。现有Maven定向验证和真实补丁→全量三服验收通过，不重复发布。
3. 出站对象扫描PASS：维护仓356个blob，总12122246字节，最大1200781字节；源码17个blob，总743502字节，最大222759字节。已核对实际私密配置值、私钥、GitHub令牌及凭据URL，无命中；无超过100MB对象。凭据仅在内存匹配，未输出或写入报告。
4. 两仓正常推送成功并由ls-remote核对SHA：维护代码及预检记录66b5af94a858c4cc2dfe31558393f82bb31f7960；IntRuoyi源码及验收记录915ffa2df04667d67e814246dd32e6629c0b40e5。维护仓本最终记录另提交后推送，再只读核对远端HEAD。

## 最终验证
- push-maintenance.json及push-intruoyi.json记录代码推送后远端与本地一致；两处远端int_main分别保持4325121b5c5126a356cb5b378c267096183a60e4和2fe66daeb63c974c0e65dd940f5afabb18f52e16。
- IntRuoyi首次推送因本地hook调用WindowsApps的Python占位程序失败，远端未创建；为本次进程补实际Python目录后，原hook完整运行，菜单迁移及端口门禁通过，推送成功。未禁用hook、未更改系统PATH、未改业务代码。
- 原实现和真实发布必要验证已有PASS；本次仅Git与任务记录，无新构建、测试或远端服务器操作，无worktree创建、合并或删除。维护仓有25个既有未推送提交加本次记录，源码6个提交；未强推或合并int_main。

## 经验门禁
- Trigger：用户明确要求提交推送本任务代码。
- Preflight check：先确认上一任务completed；核对分支、origin、staged及未提交文件归属，检查已通过的必要验证，核对待推送对象大小和敏感资料。
- Blocker：未验证实现、敏感文件、混入无关改动、推送非快进或网络认证失败时停止对应写入并保留现场。
- Verification：git diff --check、明确暂存文件、提交记录、git push返回码及远端分支SHA与本地HEAD一致。
- Forbidden action：强制覆盖、泄露凭据、提交资源包私密资料、自动合并int_main、重发三服。
- Evidence：本目录execution-log.md与最终推送结果；经验入口docs/experience-index.md及实际映射的PowerShell记忆。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，发布实现和验收记录进入所属仓库可追踪分支。
- 是否存在临时补丁或绕过：否。
