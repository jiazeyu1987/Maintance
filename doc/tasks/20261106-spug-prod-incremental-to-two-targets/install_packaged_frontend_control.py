"""Install only the exact verified constructor fix on target 58."""
import argparse,base64,hashlib,json
from common import TASK,PRIVATE,remote,write
from packaged_frontend_install_script import SCRIPT
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
 output=TASK/'packaged-frontend-target-installation-58.json';assert not output.exists()
 build=json.loads((TASK/'release-build-verification.json').read_text(encoding='utf8'))
 committed=json.loads((TASK/'packaged-frontend-implementation-commit.json').read_text(encoding='utf8'))
 assert build['status']==committed['status']=='PASS' and build['targetCommit']==committed['implementationCommit']==args.commit
 regression=json.loads((TASK/'frontend-health-regression-7.json').read_text(encoding='utf8'))
 assert regression['expectedResultObserved'] and regression['inputFilesUnchanged'] and regression['containerRemoved']
 preflight=json.loads((TASK/'packaged-frontend-upgrade-preflight-58.json').read_text(encoding='utf8'));assert preflight['status']=='PASS'
 candidate=json.loads((TASK/'frontend-readiness-candidate-58.json').read_text(encoding='utf8'));assert candidate['status']=='PASS'
 pins=[]
 for n in ('368','369','370'):pins.extend(json.loads((PRIVATE/('failed-'+n+'-all-pins.private.json')).read_text(encoding='utf8'))['pins'])
 assert len(pins)==len({p['path'] for p in pins})==2916
 failed='smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d'
 no_mutation=next(p for p in pins if p['path'].endswith(failed+'/resource-no-mutation-release.json'))
 raw=(PRIVATE/('package-'+args.commit[:7])/'backup-restore-standard.tgz').read_bytes();assert hashlib.sha256(raw).hexdigest()==build['packageSha256']
 values=dict(ROOT='/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',SUFFIX='58',COMMIT=args.commit,
  TARGET='intruoyi-main-58-safe-restore-20261104-v1',APP='intruoyi-57-safe-20261024-v1',FAILED_OPERATION=failed,
  POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',PACKAGE=base64.b64encode(raw).decode(),PACKAGE_SHA=build['packageSha256'],
  MANIFEST_SHA=build['fileManifestSha256'],PREFLIGHT=preflight,FAILURE_PINS=pins,CLEARANCE=None,LEGACY_VERIFIED=False,
  FRONTEND_PROFILE=candidate['profile'],NO_MUTATION_RELEASE=no_mutation,EXPECTED_ENDPOINTS=candidate['endpoints'])
 result=remote('172.30.30.58','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,1000)
 write(output,result);print(json.dumps(result))
