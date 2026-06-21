# Project Error Prevention Memory

- 提交前跑 TDD 钩子；execution-log 只记裸 RED/GREEN；SQL 变更补脚本和测试；证据: 20260617-release
- 部署验证不能只看健康；要核 operation、manifest、镜像、迁移状态和真实入口；证据: 20260617-release
- 真实 E2E 先记失败再统一修复并整轮复测；不要边测边改；证据: 20260618-role-e2e
- 环境部署前先核本机控制台授权、secrets、确认文本、旧 jar/陈旧 RUNNING 锁；任一前置条件缺失直接阻塞；证据: 20260620-release-flow
- 构建完成就做候选包 preflight；manifest、required SQL、dry-run/隔离工作区、多环境迁移契约先过；证据: 20260621-release-flow
- 同一发布包按多环境契约处理；test/backup 专属迁移在 prod preflight 明确跳过，SQL/迁移按真实环境基线做合同测试；证据: 20260621-release-flow
- 测试通过前先确认 AVAILABLE 恢复点；正式备份前单独校验 secrets、确认文本、DCC manifest 和 object inventory；证据: 20260620-release-flow
- 部署输入变更后必须新 releaseTag 重建并整链复测；旧候选包只作证据；证据: 20260621-flow
- 备份服路径固定 /mnt/intruoyi-data；发布前后核远端 .env、镜像与受保护对象边界；证据: 20260621-flow
