from pathlib import Path
task=Path(__file__).resolve().parent
s=(task/'release-slot.ps1').read_text(encoding='utf-8')
s=s.replace('registration-config-release-fix-20261126','fenbeitong-ticket-tenant-20261126')
s=s.replace('8090','8091').replace('48090','48091').replace(' -ne 9 ',' -ne 10 ').replace('slot 9 released','slot 10 released')
assert "$rows[0].slot -ne 10" in s
(task/'release-tenant-slot.ps1').write_text(s,encoding='utf-8')
print('Owned slot 10 closeout prepared')
