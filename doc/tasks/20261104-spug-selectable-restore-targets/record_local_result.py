"""Keep the owning task's coordination records in sync; explicit UTF-8 only."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
MAIN=Path('C:/Users/D01021/Documents/ChatGPT/Maintance')
REL=Path('doc/tasks/20261104-spug-selectable-restore-targets')

ENTRY='''

## 2026-11-04 Spug三服恢复目标本机补齐
- 用户要求：三服按次可选，正式服后续新备份自动可选恢复；已授权三服只读检查，服务器安装/数据恢复尚未授权。
- 命令意图：在独立任务worktree以BDD/TDD补主实例v2存储、safe运行合同、动态归档目录、按目标只读检查及登记计划生成器；没有连接其他应用接口或执行服务器写入。
- 验证：Linux234项通过；最后主实例Windows/Linux各29项通过；Windows safe/lightweight包及相关合同55项通过；Spug44项、JS42项、本地HTTP1项通过；diff --check通过。此前Windows Linux专用测试、Linux依赖/overlay/Git路径失败如实保留后改到正确平台验证，未静默跳过。
- 状态：本机实现保留未提交；服务器安装授权已询问，未收到答复。正式服load约1376、backend只读inspect超时仍阻断就绪；未修复、重启或恢复，不宣称完成。工作区为C:/Users/D01021/.codex/worktrees/spug-restore-targets/Maintance，分支codex/spug-selectable-restore-targets-20261104，base=9a62391。
- 安装范围和待验前提：doc/tasks/20261104-spug-selectable-restore-targets/installation-plan.md。所有凭据保留于私密目录，无凭据内容进入本记录。
'''

if __name__=='__main__':
    for root in (ROOT,MAIN):
        path=root/'docs/request-command-log.md'
        content=path.read_text(encoding='utf-8')
        if '## 2026-11-04 Spug三服恢复目标本机补齐' not in content:
            path.write_text(content+ENTRY,encoding='utf-8')
        assert ENTRY.strip() in path.read_text(encoding='utf-8')
    # Only documentation owned by this task is mirrored. Product changes stay
    # isolated; unrelated main-workspace documents and code are never copied.
    for name in ('task.md','design.md','execution-log.md','installation-plan.md',
                 'storage-execution-log.md','main-runtime-execution-log.md','readonly-recheck.json'):
        raw=(ROOT/REL/name).read_text(encoding='utf-8')
        destination=MAIN/REL/name
        destination.write_text(raw,encoding='utf-8')
        assert destination.read_text(encoding='utf-8')==raw
    print('OWN_TASK_DOCUMENTS_UTF8_SYNCED')
