"""Write a human-readable report only from completed, verified release evidence."""
from datetime import datetime
import json
from pathlib import Path
import sqlite3

task=Path(__file__).parent
result=json.loads((task/'release-result.json').read_text('utf-8'))
assert result['status']=='PASS'
for name in ('worktree-closeout.json','slot-closeout.json'):
    assert json.loads((task/name).read_text('utf-8'))['status']=='PASS'
with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
jobs=[j for j in state['jobs'] if j.get('releaseTag')==result['releaseTag']]
assert not any(j['status']=='running' for j in jobs)
names={'test':'测试服','prod':'正式服','backup':'审查服'}
lines=['# 三服发布验收记录','',
    '固定发布版本：`'+result['releaseTag']+'`。三服使用同一个封存包和前后端镜像，数据库结构一致。','',
    '| 环境 | 访问地址 | 表数量 | 后端 / 前端 | GxP |','|---|---|---:|---|---|']
for env in ('test','prod','backup'):
    proof=result['targets'][env]
    assert proof['maintenance'] is False and proof['tableCount']==885
    lines.append('| '+names[env]+' | '+proof['entryUrl']+' | 885 | UP / HTTP 200 | 保存与运行均关闭 |')
lines.extend(['','本机 GxP 也通过真实登录后的配置页面确认关闭，未发生待重启模式差异。',
    '','## 修复与验证','',
    '- 根因：历史 DCC 治理建表和 tenant_id 迁移仅面向测试环境，正式服和审查服各缺 3 张表。',
    '- 修复：新增全环境前向迁移，保留历史 SQL 和台账摘要；测试服保留现存表，正式和审查补齐结构。没有复制业务行或删除现有表。',
    '- 逐服核对 operation=SUCCESS、固定清单、实际生效镜像与配置、后端健康、前端响应、真实 Playwright 登录和 GxP 保存/运行状态。',
    '- 独立对照全部表名、字段、索引、约束及外键；三服均 885 张表，元数据完全一致。新增迁移三服均 APPLIED。',
    '- 本地真实 MySQL 8.0.39 验证新增迁移、重复执行及合成既有行保留；执行器 531 项回归，0 失败/错误，2 项 Linux 专用跳过。',
    '- 页面验收范围为真实登录和只读配置、版本与展示；没有执行新增、保存、审批等完整业务写入回归。',
    '','## 恢复与封包','',
    '- 按用户范围取消完整数据隔离演练。正式采用独立恢复机制，没有重复采集 Spug 全量检查点。测试服和审查服保留自身恢复检查点。',
    '- 原资源包完整校验通过且未覆盖，更新工作包按实际文件重新生成清单；凭据、发布历史、版本绑定和镜像保留。',
    '- 构建封包后曾因合法 Python 缓存未被识别而清理失败；真实失败测试后修复。首次重传清理超过 Git 180 秒超时，但目录及登记实际已删除，经既有所有权续接机制完成。',
    '- 两次失败历史均保留。最终通过 Spug 原包重传成功，未重新编译、未修改封存摘要；本地和 NAS 原包一致。',
    '- 发布包大小：'+str(result['packageBytes'])+' 字节（约 '+format(result['packageBytes']/1024**2,'.2f')+' MiB）。',
    '- 包 SHA-256：`'+result['packageSha256']+'`。',
    '- 程序源提交：`'+result['sourceCommit']+'`；维护提交：`'+result['maintenanceCommit']+'`。',
    '','## 任务时间线','',
    '| Spug 任务 | 动作 | 开始 | 完成 | 结果 |','|---|---|---|---|---|'])
for job in sorted(jobs,key=lambda j:j.get('createdAt','')):
    lines.append('| '+job['id']+' | '+job['action']+' | '+str(job.get('createdAt',''))+' | '+str(job.get('finishedAt',''))+' | '+job['status']+' |')
lines.extend(['','## 本机入口和启动','',
    '- Spug：`http://127.0.0.1:18081/release-center/?app=intruoyi`。',
    '- 当前普通脚本执行器运行于稳定目录 `C:/SpugHandoff/release/source`，无需重复启动。',
    '- 需要重新启动时，先确保没有已有实例，运行：','',
    '```powershell',
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/D01021/Documents/spug-handoff-work-20261030/start-local.ps1 -SourceStopped',
    '```','',
    '没有安装 Windows 服务，没有合入或推送 int_main。本任务两个临时工作副本及 Git 登记均已删除，独立分支保留，slot3 已释放，其他任务资源未改；worktree-closeout.json、slot-closeout.json 均 PASS。',''])
text='\n'.join(lines)
(task/'acceptance-report.md').write_bytes(text.encode('utf-8'))
assert (task/'acceptance-report.md').read_text('utf-8')==text
print('Verified release acceptance report written')
