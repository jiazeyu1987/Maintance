# 发票打印助手发布配置

通用前端包不包含环境专属打印地址。应用通过已鉴权状态接口返回 `publicUrl`，发布目标可在私密配置的 `targets.<environment>.invoiceVoucherPrintAssistantUrl` 显式登记浏览器地址。

- Trigger：发布包含运行期打印地址合同的新应用，或变更目标打印助手地址。
- Preflight check：确认目标、实际助手服务、浏览器公开 URL、后端独立 assistant-host；从后端网络验证助手响应。公开 URL 必须是该已登记主机的 HTTP(S) 根地址，端口 18733。核启动命令消费 JAVA_OPTS。没有登记不自动猜地址。
- Blocker：非法 URL、跨目标地址、演练目标、启动合同不符、内部助手不可达或应用尚未支持运行期配置；在停服前处理。
- Verification：在独立维护 worktree 运行 `python -X utf8 -B -m unittest test_invoice_print_runtime_config test_fenbeitong_integration_config test_clone_network_config`；正常发布及开放后的 JVM 属性只含一次 `yudao.erp.invoice-voucher-print-assistant.public-url`，旧 CLI 同名覆盖移除，其余环境与内部 assistant-host 保留；最终真实登录打印页面核公开地址与权限。
- Forbidden action：不把环境 IP 写进跨环境前端包，不修改恢复配置原件，不从 public URL 推断后端探测 host，不修改已封存包，不用 HTTP 200 替代权限与实际页面验证。
- Evidence：`doc/tasks/20261123-update-test-release/execution-log.md`；实际容器替换/开放、配置重复、非法地址拒绝测试见 `test_invoice_print_runtime_config.py`。

阶段必查：构建前确认应用合同和固定提交；安装前确认无活动发布、备份执行器及私密配置并保留 ACL；部署前由正式 preflight 校验目标配置；部署后核真实容器及页面。记录目标、提交、原配置摘要、变更键、测试结果和实际验收，凭据仅留私密目录。Fail Fast 按以上 Blocker，不覆盖历史失败记录。
