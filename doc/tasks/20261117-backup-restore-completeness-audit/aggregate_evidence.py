"""Summarize immutable audit outputs without treating partial checks as PASS."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
def read(name):
    return json.loads((root/name).read_text(encoding='utf-8'))
observations={}
differences={}
for path in sorted(root.glob('target-data-*.json')):
    doc=json.loads(path.read_text(encoding='utf-8'))
    assert not set(observations).intersection(doc['observations']), 'OVERLAPPING_TABLE_OBSERVATIONS'
    observations.update(doc['observations'])
    differences.update(doc['differences'])
large=[json.loads(path.read_text(encoding='utf-8')) for path in root.glob('target-large-*.json')]
large.sort(key=lambda x:x['start'])
position=0
digests=[]
for doc in large:
    assert position==doc['start'], 'LARGE_TABLE_RANGE_GAP_OR_OVERLAP'
    position=doc['end']
    assert len(doc['rowDigests'])==doc['end']-doc['start']
    digests.extend(bytes.fromhex(v) for v in doc['rowDigests'])
large_complete=bool(large) and position==large[0]['expected']['rows']
large_equal=False
if large_complete:
    digest=hashlib.sha256(b'row-multiset/v1\n')
    for value in sorted(digests):digest.update(value)
    actual={'rows':len(digests),'jsonNodes':sum(x['jsonNodes'] for x in large),'multisetSha256':digest.hexdigest()}
    large_equal=actual==large[0]['expected']
    observations[large[0]['table']]=actual
    if not large_equal:differences[large[0]['table']]={'expected':large[0]['expected'],'actual':actual}
files=[json.loads(path.read_text(encoding='utf-8')) for path in sorted(root.glob('target-files-*.json'))]
missing=[n for x in files for n in x['missingFiles']]
hash_differences=[n for x in files for n in x['hashDifferences']]
counts=read('target-all-counts.json')
historical=read('target-historical-data.json')
out={'tableCounts':{k:v for k,v in counts.items() if k not in ['expectedCounts','actualCounts']},'contentTablesChecked':len(observations),'contentTablesMatchingFrozenPoint':len(observations)-len(differences),'contentDifferences':differences,'appendOnlyHistoricalRows':{'checked':historical['tablesChecked'],'matching':historical['matchingTables'],'differences':historical['differences']},'largeTable':{'rowsChecked':position,'complete':large_complete,'equal':large_equal},'physicalFiles':{'expected':files[0]['expectedTotalFiles'],'contentChecked':sum(x['contentChecked'] for x in files),'missing':len(missing),'missingBusinessFiles':[n for n in missing if not n.startswith('.minio.sys/')],'businessHashDifferences':[n for n in hash_differences if not n.startswith('.minio.sys/')],'internalHashDifferences':[n for n in hash_differences if n.startswith('.minio.sys/')],'businessFilesHashed':sum(v for x in files for k,v in x['bucketCheckedCounts'].items() if k!='.minio.sys'),'bytesHashed':sum(x['bytesHashed'] for x in files)},'schema':read('target-schema.json'),'backupBoundary':read('source-boundary.json'),'scopeGaps':read('source-scope-gaps.json')}
(root/'audit-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k not in ['backupBoundary','scopeGaps','contentDifferences']},ensure_ascii=False))
