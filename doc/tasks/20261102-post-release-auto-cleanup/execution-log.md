# 执行记录

- 用户授权修改发布后旧包/旧恢复载荷自动清理；已先建任务文档。前序说明任务completed，无遗留执行进程。
- Bootstrap读取适用规则和经验索引；绝对路径Join-Path首读报路径格式错误，随后按绝对路径成功读取powershell-memory，未发生写入或外部动作。后续路径先判断绝对/相对，避免包装错误。
# BDD 与实现工作副本

- 工作副本：`C:/Users/D01021/.codex/worktrees/spug-post-release-cleanup/Maintance`；分支 `codex/post-release-auto-cleanup-20261102`。
- 基线：8797d66（配套完整发布/补丁/手动清理代码）与当前 int_main c470b9a 在独立副本正常合并，无冲突。没有覆盖主工作区脏改动；运行副本仍含独立修复，后续仅同步本任务定向改动。
- BDD: Given 同一完整包或前端补丁已完成三服最终验收，When 收尾，Then 自动清理已知失效旧载荷，保留当前包及本次恢复点、清单与历史。
- BDD: Given 发布失败、仅部署未验收、未完成三服、存在活动/未解决任务或演练引用，When 收尾，Then 不触发清理或保护对应版本。
- BDD: Given 已登记的旧包与恢复记录，When 清理，Then 逐普通文件复核身份和SHA，保留凭据、记录、当前恢复点及未知资料；不删除NAS、数据卷或容器。
- BDD: Given 部分删除后遇到摘要/磁盘错误，When 清理停止，Then 清理单独标记失败并保留已删清单，发布成功状态不被篡改，后续可从真实剩余文件继续。
- RED: `python -X utf8 -m unittest test_post_release_cleanup -q` -> FAIL，预期缺少 post_release_cleanup 模块。
- GREEN: experience-preflight -> PASS（本地临时普通文件删除测试；没有三服写入、发布或业务E2E）。

- REGRESSION: 已对齐8797d66与6e36019配套分支，文档并集及UI直发流程/现场版本参数冲突已审阅解决。569项Python测试通过（2项已有skip），Windows服务专用模块因普通脚本运行环境无pywin32明确排除；未伪装服务测试通过。Node远端UI合同通过。
- Linux真实测试：8项PASS（7项真实临时文件删除、安全保留与失败记录，加1项真实多进程flock；重试子目录和规范暂存根共锁）。Linux容器无psutil，控制器全套测试在Windows实际依赖环境执行，不以Linux缺依赖失败充当成功。
- 载体错误记录：早期两次命令工作目录重复前缀/错误测试模块名导致非业务失败，已更正实际路径与模块；未修改产品以适应错误载体。
- GREEN: experience-preflight -> PASS，允许在0活动发布任务时备份7个代码文件并定向更新本机普通脚本执行器。保留配置SHA与SQLite逻辑状态完整一致、所有历史/包绑定和三服状态不写入；不安装服务、不做真实三服发布或删除测试。

- GREEN: 最终源码定向184项PASS，匹配现有运行器的候选副本同样184项PASS。已在0运行任务时停止唯一已核身份的18112普通Python、备份代码、精确更新7个文件并由原稳定start-local.ps1隐藏启动；没有服务安装。
- GREEN: apply-runtime-update.py verify -> PASS，Spug18081 HTTP200，18112认证state正常；私密配置和SQLite逻辑SHA不变，271任务/28完整包/1补丁。未调用三服，不把本地测试称作真实三服清理验收。
- Current Status: ready_for_closeout；后续只剩实现提交、int_main融合复验、独立worktree收口与最终记录提交。
