"""Read one already pinned original launcher reply without invoking an owner."""
import hashlib,json
from common import TASK,PRIVATE,remote
from verify_automatic_source_restoration import read_pinned,write_exclusive

if __name__=='__main__':
    original,diagnostic_pin=read_pinned(PRIVATE/'automatic-full373-dispatch-contract-diagnostic.private.json')
    reference=original['records']['execute/native-original-exit.json']['value']['resultPin']
    private=PRIVATE/'automatic-full373-launcher-reply.private.json'
    public=TASK/'automatic-full373-launcher-reply-diagnostic.json'
    assert not private.exists() and not public.exists()
    code='REFERENCE='+repr(reference)+'''\nimport hashlib,json,pathlib
path=pathlib.Path(REFERENCE['path']);assert path.resolve(strict=True)==path and not path.is_symlink()
raw=path.read_bytes();assert len(raw)==REFERENCE['bytes'] and hashlib.sha256(raw).hexdigest()==REFERENCE['sha256']
print(json.dumps(json.loads(raw)))
'''
    reply=remote('172.30.30.57',code,30)
    write_exclusive(private,reply)
    summary=dict(status='OBSERVED',originalReplyPin=reference,diagnosticPin=diagnostic_pin,
        originalReply=reply,noServerMutation=True,actualAuditRerun=False)
    write_exclusive(public,summary)
    print(json.dumps(summary))
