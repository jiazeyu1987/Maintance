"""Keep the failed remote proof private and report only its static assertion."""
from pathlib import Path
import json,re,sys
path=Path(__file__).with_name('verify-patch-remote-proof.py')
scope={'__file__':str(path),'__name__':'__diagnostic__'}
try:
    exec(compile(path.read_text('utf-8'),str(path),'exec'),scope)
except AssertionError:
    result=scope.get('result')
    assert result is not None and result.returncode!=0
    private=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/proof-'+sys.argv[2]+'.private.log')
    assert not private.exists()
    private.write_bytes(result.stdout+b'\n'+result.stderr)
    lines=re.findall(rb'File "<stdin>", line (\d+)',result.stderr)
    number=int(lines[-1]) if lines else None
    statement=scope['code'].splitlines()[number-1].strip() if number else ''
    assert not statement or statement.startswith(('assert ','container=','fence=','deployment=','result='))
    print(json.dumps(dict(status='FAIL',remoteExitCode=result.returncode,line=number,staticStatement=statement)))
