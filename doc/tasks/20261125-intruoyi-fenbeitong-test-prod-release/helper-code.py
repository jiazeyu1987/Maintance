import json
import re
from pathlib import Path
root=Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125')
v=json.loads((root/'test-helper-connectivity.private.json').read_text(encoding='utf-8'))
lines=v['probe']['files'][0]['source'].splitlines()
hits=[i for i,x in enumerate(lines) if 'async function handleAuthCallback' in x or 'TICKET_VALIDATE_URL' in x]
selected=set()
for i in hits:selected.update(range(max(0,i-8),min(len(lines),i+75)))
for i in sorted(selected):print(str(i+1)+': '+lines[i])
print('Log error classifications:',json.dumps([re.sub(r'(https?://[^\s?]+)\?\S+',r'\1?<redacted>',x) for x in v['logs'].splitlines() if ('ticket' in x.lower() or 'callback' in x.lower()) and ('error' in x.lower() or 'fail' in x.lower())],ensure_ascii=False))
print('Backend auth exception classes:',json.dumps([x for x in v.get('backendLogs','').splitlines() if ('注册证' not in x and (re.match(r'^[a-zA-Z][a-zA-Z0-9_.]*(Exception|Error):',x) or x.startswith('Caused by:') or ('at ' in x and 'validateFenbeitong' in x)))],ensure_ascii=False))
