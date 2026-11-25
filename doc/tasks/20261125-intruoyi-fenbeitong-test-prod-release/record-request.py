from pathlib import Path

root = Path(__file__).resolve().parents[3]
text = '''

## 2026-11-25 IntRuoyi 分贝通修复测试/正式发布

- 用户需求：发布 intruoyi 到测试服务器和正式服务器；不扩大到审查服或分贝通助手重新发布。
- 命令意图：固定应用 e1ccafbc6638e64f544e609f9072096f529e45b2、维护 ea06ce8983d2330f9fab478551209582c11582fe；新建隔离 worktree；先验证并安装已提交的运行时地址脚本，再以正式动作 build-release -> publish-test -> mark-tested -> promote-prod -> accept-prod 推进同一包。
- 前置结果：24 项配置回归 PASS；实际执行器原子安装、ACL/配置/历史及非目标文件保持 PASS；测试与正式真实登录基线 PASS；构建 JOB-b2f69a51ce，版本 2026-11-25-23-53-05，后续结果见 doc/tasks/20261125-intruoyi-fenbeitong-test-prod-release/。
- 凭据仅在本机保护配置内读取，不记录明文；既有无关改动保持。
'''
with (root/'docs/request-command-log.md').open('a',encoding='utf-8') as log:
    log.write(text)
assert text in (root/'docs/request-command-log.md').read_text(encoding='utf-8')
print('Request and command intent recorded in UTF-8')
