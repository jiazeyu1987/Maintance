# Test Plan：DCC 短编码文件名直连识别硬化

## BDD Scenarios

- `BDD: 短编码嵌入普通长 token 时不得直连 -> Given 启用项目编码中存在 IN / When 文件名是 INT-培训记录.pdf / Then 服务不得把 IN 当作唯一项目编码直接回写。`
- `BDD: 低置信度短编码必须继续正式识别链路 -> Given 启用项目编码中存在 EC / When 文件名是 EC-现场记录.pdf / Then 服务不得跳过内容识别直接回写。`
- `BDD: 长编码边界清晰时仍保留快捷路径 -> Given 文件名包含唯一长编码 RE-STM-MM-017-04 / When 文控执行识别 / Then 服务直接命中长编码并跳过文件内容读取。`
- `BDD: 同长度歧义命中不得强行直连 -> Given 文件名同时命中多个同长度边界有效编码 / When 服务评估文件名 / Then 必须放弃直连。`

## RED

- `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileProjectCodeRecognitionServiceTest -Dsurefire.failIfNoSpecifiedTests=false test`
  - 预期：新增的短编码误命中测试先失败，证明当前 `containsIgnoreCase` 规则确实会把低置信度子串当成直连命中。

## GREEN

- `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileProjectCodeRecognitionServiceTest -Dsurefire.failIfNoSpecifiedTests=false test`
- `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileProjectCodeRecognitionServiceTest,DccProjectCodeCodexCliClientImplTest -Dsurefire.failIfNoSpecifiedTests=false test`

## REGRESSION

- 如进入测试服联调：选取一个长编码样本和一个短编码风险样本，验证“长编码仍可直连、短编码不再误直连”。

## E2E

- 本任务主验收以 backend 单测为主。
- 若与第二任务合并联调，最终 E2E 必须通过真实 DCC 前端路径或真实 API 样本验证，不允许只看日志推断。

## Test Data

- 风险样本文件名：`INT-培训记录.pdf`、`OCP-检验记录.xlsx`、`ECR-变更申请.docx`
- 正常长编码样本文件名：`RE-STM-MM-017-04（A0）万级浮游菌控制趋势图.pdf`
- 只读辅助 SQL：
  - `SELECT CHAR_LENGTH(TRIM(project_code)) AS code_len, COUNT(*) FROM dcc_project_code WHERE status = 1 AND project_code IS NOT NULL AND TRIM(project_code) <> '' GROUP BY CHAR_LENGTH(TRIM(project_code)) ORDER BY code_len;`

## Failure Paths

- 短编码作为普通长 token 子串被误命中。
- 两位短编码作为独立段落仍被错误放行为直连。
- 多个同长度候选同时命中时仍强行选一个回写。
- 规则收紧后意外破坏既有长编码直连能力。
