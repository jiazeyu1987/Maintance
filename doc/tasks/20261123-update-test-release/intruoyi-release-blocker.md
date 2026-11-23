# IntRuoyi 发布输入缺口

## 目标提交
bd01f08cdf8c36a443664d750842705d41cb3632，已通过代理 fetch 并 fast-forward 到 int_main。

## 问题
目标提交新增以下正向迁移，但未在 IntRuoyiBackend/sql/mysql/release-sources.json 登记：

- 20261123_dcc_registration_certificate_ce_reminder_thresholds.sql
- 20261123_dcc_registration_certificate_ce_supporting_materials.sql
- 20261123_dcc_registration_certificate_supporting_status_effective.sql

发布执行器 release_source_catalog.release_paths 对全部 20*.sql 强制唯一归宿，缺登记将报 SQL catalog mismatch。不能跳过这些 SQL 或修改发布检查器放行。

## 需要 IntRuoyi 完成
1. 审核并补充三条 SQL 的正式发布归宿，确认依赖及目标数据前置条件；最后一条收紧 supporting_document.status，尤其应核旧状态是否存在。
2. 在固定提交的独立工作区运行 scripts/preflight/test_release_source_registration.py，并通过正式迁移解析和必要业务验证。
3. 提交并推送修复，提供新的提交号和验证结果；维护发布任务再从新提交构建，测试服目标预检通过后部署。

按用户既有分工，应用实现由 IntRuoyi 负责，维护任务负责发布输入校验、部署与验收。本文件仅整理交接问题，未代发消息、未修改应用或服务器数据。
