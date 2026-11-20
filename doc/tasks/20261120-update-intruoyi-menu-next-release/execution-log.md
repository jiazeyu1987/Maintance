# 执行记录

- 用户要求：更新IntRuoyi代码；下次发布修复菜单。
- 范围：Git更新与下次发布计划登记；不立即发布或改数据库。
- GREEN: experience-preflight -> PASS。现行配置与前后端rev-parse均确认单一IntRuoyi根仓库；分支int_main。代理fetch成功，远端9783f8fc2，本机bff7ec4c2，本机独有11/远端独有19提交。merge-tree无冲突，合成树892f4b4ed624ae5e19ac7447939c6e25abb410a1；更新前私密记录脏文件SHA，不覆盖、不自动stash。
- 第一次merge因4个未提交路径交叠安全拒绝，无冲突文件。检查差异后仅对这4个路径建立命名stash 41e7f3ce，再执行合并；其他用户文件不纳入合并提交。
- 首次hook默认python未成功，补实际已安装Python路径后正常git commit，未禁用hook；菜单登记检查598项通过，端口守卫int_main 8081/48081通过。合并提交46c87dd2c。
- stash apply成功且无冲突；逐文件比较原stash差异新增/删除行与恢复后差异完全相等。首次字节核验揭示Git转换12个非交叠文件LF/CRLF，只有规范化后SHA与原值严格相等才还原原字节；最后确认非交叠文件26个原SHA保留，4个交叠文件本地改动保留。
- GREEN: 远端祖先检查 -> PASS；应用暂存区空、无未合并文件。未推送本地12个提交，不提交用户脏改动。
- 新增下次发布门禁docs/next-release-menu-repair.md，链接至发布checklist/经验索引；列明授权、待办状态、阶段必查、Fail Fast、验证与禁止操作。菜单未修复，待下一次发布实施。
- GREEN: 文档diff检查 -> PASS。无本任务worktree/运行控制台需要清理；stash已恢复但保留恢复副本。本任务更新与登记完成，实际菜单修复仍pending_next_release。
