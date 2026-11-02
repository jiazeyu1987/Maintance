"""Wait on a specific persisted job, emitting only bounded progress metadata."""
import json
from pathlib import Path
import sqlite3
import sys
import time

identity=sys.argv[1]
while True:
    with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:
        state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
    job=next(j for j in state['jobs'] if j['id']==identity)
    print(json.dumps({k:job.get(k) for k in ('id','action','releaseTag','status','currentStep','finishedAt')}),flush=True)
    if job['status']!='running':
        sys.exit(0 if job['status']=='succeeded' else 1)
    time.sleep(45)
