"""Prepare only this task's experience additions on its committed base."""
from pathlib import Path
import subprocess

task=Path(__file__).parent
workspace=task.parents[2]
repo=Path('C:/SpugHandoff/schema-ops-20261101')
base='43e4d3eb6b85d4f54749d721ad4ec977102a4747'
heading='三服同版本同结构发布门禁'
route='- 三服表数不同 / 环境限定建表 / 治理表仅test / 同包升级后结构一致 / expectedSchemaSha256：`docs/release-agent-checklist.md#三服同版本同结构发布门禁`；修复用不可变前向迁移，不改已执行SQL，不删表凑数量；升级后核表、列、索引与约束，保留各自业务数据和迁移历史。'
gate=(task/'release-consistency-gate.md').read_text('utf-8')
section=gate.replace('# 三服版本与结构一致性发布门禁','## '+heading,1).replace('## 阶段必查项与推荐命令','### 阶段必查项与推荐命令',1)
directory=task/'doc-commit-inputs'
directory.mkdir(exist_ok=True)
for name,addition in [('experience-index.md',route+'\n'),('release-agent-checklist.md',section)]:
    relative='docs/'+name
    original=subprocess.check_output(['git','-C',str(repo),'show',base+':'+relative]).decode('utf-8').replace('\r\n','\n')
    first,rest=original.split('\n',1)
    updated=first+'\n\n'+addition.strip()+'\n'+rest
    assert updated.count(addition.strip())==1
    (directory/name).write_bytes(updated.encode('utf-8'))
    target=workspace/relative
    shared=target.read_text('utf-8')
    if name=='experience-index.md':
        lines=shared.splitlines()
        matches=[i for i,line in enumerate(lines) if line.startswith('- 三服表数不同 / 环境限定建表 / 治理表仅test /')]
        assert len(matches)==1
        lines[matches[0]]=route
        target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    else:
        assert '## '+heading not in shared
        first,rest=shared.split('\n',1)
        target.write_text(first+'\n\n'+section.strip()+'\n'+rest,encoding='utf-8')
print('Prepared two owned experience additions; unrelated shared edits remain outside the task commit')
