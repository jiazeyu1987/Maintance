# 后端补丁衔接全量发布验收

状态：completed，2026-11-03。

先完成后端补丁 `2026-11-03-10-33-18` 三服发布，再完成同源码全量 `2026-11-03-12-15-42`；原失败记录及实际重试关联均保留。

| 环境 | 访问地址 | 最终版本 | 健康 / 页面 | GxP |
|---|---|---|---|---|
| 测试服 | http://172.30.30.58:8081 | 2026-11-03-12-15-42 | UP / 200 | 关闭 |
| 正式服 | http://172.30.30.57:8081 | 2026-11-03-12-15-42 | UP / 200 | 关闭 |
| 备份服 | http://172.30.30.59:38081 | 2026-11-03-12-15-42 | UP / 200 | 关闭 |

源码固定 `ee2d7c79356e79e1180ab03e03873cd3f924a6f5`。补丁JAR SHA为`8c3c670d57c77c84d76fe335e3918e1a9f4cd5b47ba097fe10908ab07c7d9135`；全量重新编译JAR SHA为`c2b08ecb22f19c65d36e9ffcf4b3464a3d214e434b467f6f44be9fd5aa1fb696`。两者源码相同；全量吸收日志/DCC/展厅/Quartz修复后，移除旧补丁程序挂载，实际运行新镜像内JAR。三服全量JAR和镜像一致，启动完成日志各1次。

三服885表、15594列、5480索引及约束/触发器等13段结构一致，各自原迁移历史保持。本轮SQL APPLY=0；测试服原有4条测试租户限定历史继续保留，未伪造跨服历史。后端补丁发布脚本没有迁移、改表或配置/业务SQL；先维护只读探针，再解除本任务保护正常启动。正式既有Quartz15秒心跳已真实验证推进，正常运行不作全库零写入承诺。

真实Playwright登录维护和开放入口、真实版本对话框及变更说明通过；本地和三服保存/运行GxP均DEVELOPMENT_DISABLED，auditEnabled=false，无待重启。这里只验收登录、展示和权限入口，没有新增/保存/审批写入功能回归。

发布后清理原JOB-7f32aa47ab失败、重试JOB-a7a180c9c4部分成功，最终JOB-763953cdce三服成功。合计删除旧文件36638007347字节，约34.12GiB；镜像共享层不按逻辑大小重复计数。测试服2026-10-22-01-09-56、10-45-28、20-45-19缺清单，以及2026-10-31-19-13-08旧恢复日志与归档绑定不一致，四组及其依赖完整保留。没有补写清单/摘要、删除NAS或正在使用的演练。正式/备份旧资源按精确身份回收，当前及最近恢复点保留。

必要实现修复已独立提交：维护仓a93fe3e（停止态补丁取证和同包检查点续接）、5f9cf1e（挂载无序身份和旧恢复组保留）、9638d6e（缺旧清单组保留）；相关164项、随后142项及真实Docker、Linux锁测试PASS。Java DCC118/展厅15/Quartz63项回归PASS。构建封包后Git清理超时通过校验原包续传处理，没有重新编译掩盖原失败。

全部本轮临时构建副本已删除，无新提交；目标开发分支保留，不自动融合或推送int_main。普通脚本执行器PID14264从稳定路径运行，18112；Spug http://127.0.0.1:18081 。未安装Windows服务。配置/凭据原样保留，原始日志和截图仅留private。

普通启动命令（只在现有进程已停止时使用）：

```powershell
& 'C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14/python.exe' 'C:/SpugHandoff/release/source/ops/spug/release-center/intruoyi_executor.py' --config 'C:/SpugHandoff/release/executor.private.json'
```

证据：final-verification.json核61份远端持久回执且worker均停止；program-full-*.json、ui-gxp-full-*.json、database-full.json、quartz-heartbeat-full.json、runtime-safety-full-cleanup-final.json及closeout-verification.json。凭据不进入报告或Git。
