"""Print only sanitized observations; keep raw browser evidence private."""
import json
import re
import sys
from pathlib import Path

root=Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125')
def clean(value):
    if isinstance(value,str):
        return re.sub(r'(https?://[^\s"<>?]+)\?[^\s"<>]*',r'\1?<redacted>',value)
    if isinstance(value,list):return [clean(v) for v in value]
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    return value
for filename in sys.argv[1:]:
    p=root/filename
    v=json.loads(p.read_text(encoding='utf-8'))
    print(json.dumps(clean(dict(file=filename,status=v['status'],error=v.get('error'),observations=v['observations'])),ensure_ascii=False))
