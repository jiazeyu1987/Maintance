# 执行记录
用户授权仅发布测试服务器。先核实际发布入口与私密配置路径；不记录凭据。

GREEN: experience-preflight -> PASS（维护隔离工作区）。固定维护bca51d5，创建C:/SpugHandoff/release/current-contract-test-20261124；无应用服务启动。执行器另建本次应用固定提交构建worktree。此前正式任务阻塞不影响本次明确仅测试服范围。

GREEN: experience-preflight -> PASS（固定提交本地构建，非全环境预检PASS）。JOB-eaa6add116仅backup59检查失败；所有本地构建/test58前置通过。59不在本次范围，构建只消费已登记历史，不修目录或登记。源码21f7528固定；实际Playwright admin登录PASS，外部统计及头像3条观察保留。构建通过后再做本包publish-test专用预检。

构建JOB-a5df794723；新tag=2026-11-24-15-38-40；应用worktree C:/SpugHandoff/release/build/2026-11-24-15-38-40、固定21f7528。构建命令由build-release入口执行mvn clean package及Vite build，均在临时目录；登记测试python -X utf8 -B scripts/preflight/test_release_source_registration.py -> 2 PASS。维护worktree current-contract-test-20261124固定bca51d5，未产生新提交。

GREEN: build-release -> JOB-a5df794723 succeeded；构建目录25200 tracked文件已核验并删除，无新提交。包契约SQL遵循已提交sql/mysql/.gitattributes的CRLF规则，manifest SHA d5fe5fa2f870669df5976aba65fbf0768966221d3cd8da794ef5614aab3f25d8；不是Git blob SHA。
GREEN: experience-preflight -> PASS（publish-test）。本包专用预检JOB-3009d55aa5全部通过，真实admin登录基线已通过，恢复资源/磁盘/起点/迁移计划通过。只发布测试58，原tag与恢复原件按执行器保留，不执行mark-tested或正式/审查晋级。

GREEN: publish-test -> SUCCESS，JOB-dcd994c924/OP-8bf34a876874b7a604f6；技术全项通过，三阶段契约回执与规范manifest identity一致。真实Playwright菜单/版本/说明/打印入口PASS_WITH_OBSERVATIONS，详见acceptance.md。
GREEN: experience-preflight -> PASS（最终维护worktree清理）。固定bca51d5、无新提交、执行器稳定source，原正式任务资产保持；外置清理回执。

GREEN: closeout -> PASS。维护worktree HEAD bca51d5，无新提交无需融合；5291文件核验、Git删除退出0、登记与目录不存在；应用构建worktree已自动清理；稳定执行器PID21804路径未变。任务completed，仅测试服发布成功。
