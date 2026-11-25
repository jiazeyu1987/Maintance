import json
from pathlib import Path

task=Path(__file__).resolve().parent
private=Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125')
for env in ('test','prod'):
    original=private/(env+'-menus.private.json')
    target=private/(env+'-menus-before.private.json')
    assert not target.exists()
    target.write_bytes(original.read_bytes())
old=task.parent/'20261125-fenbeitong-runtime-url-fix/release-slot.ps1'
script=old.read_text(encoding='utf-8').replace('fenbeitong-runtime-url-20261125','registration-config-release-fix-20261126').replace('.fenbeitong-url-','.registration-release-')
(task/'release-slot.ps1').write_text(script,encoding='utf-8')
print('Preserved two menu baselines and prepared exact owned-slot cleanup')
