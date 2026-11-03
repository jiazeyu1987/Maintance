"""Preserve installed UI variant; install the one reviewed closure disposition."""
import base64,hashlib,json,subprocess,sys
from pathlib import Path
private=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/runtime-interruption')
container='intruoyi-spug-handoff-20261030-spug-1'
target='/var/lib/intruoyi-spug/releases/dbabf7e/ui/app.js'
def sha(data):return hashlib.sha256(data).hexdigest()
def docker(code,data=None):
    result=subprocess.run(['docker','exec','-i',container,'python3','-c',code],input=data,capture_output=True,timeout=30)
    assert result.returncode==0,'UI file operation failed; raw output withheld'
    return result.stdout
raw=base64.b64decode(docker('from pathlib import Path;import base64;print(base64.b64encode(Path('+repr(target)+').read_bytes()).decode())'))
before="['close-build','close-pre-effect','verify-deployment','verify-opening','verify-checks'].includes(evidence?.disposition)"
after=before.replace("'verify-checks']","'verify-checks','verify-backend-restoration']")
if sys.argv[1]=='prepare':
    text=raw.decode('utf-8');assert text.count(before)==1 and after not in text
    updated=text.replace(before,after).encode('utf-8')
    (private/'served-app-before.private.js').write_bytes(raw)
    (private/'served-app-candidate.private.js').write_bytes(updated)
    (private/'served-ui-plan.json').write_text(json.dumps(dict(path=target,before=sha(raw),after=sha(updated)),indent=2),encoding='utf-8')
    print(json.dumps(dict(status='prepared',onlyDispositionChanged=True)))
elif sys.argv[1]=='install':
    plan=json.loads((private/'served-ui-plan.json').read_text('utf-8'))
    updated=(private/'served-app-candidate.private.js').read_bytes()
    assert sha(raw)==plan['before'] and sha(updated)==plan['after']
    payload=json.dumps(dict(path=target,before=plan['before'],data=base64.b64encode(updated).decode())).encode('ascii')
    docker('import base64,hashlib,json,os,sys;from pathlib import Path;p=json.load(sys.stdin);f=Path(p["path"]);assert hashlib.sha256(f.read_bytes()).hexdigest()==p["before"];t=f.with_suffix(".js.interruption-update");t.write_bytes(base64.b64decode(p["data"]));os.replace(t,f)',payload)
    print(json.dumps(dict(status='installed',onlyDispositionChanged=True,sha256=plan['after'])))
else:raise SystemExit('Unknown phase')
