import hashlib, json, os
from pathlib import Path
TASK=Path(r'D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260806-head-test-only-release')
PKG=Path(r'E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260806-intmain-head-test-r260806c-r1')
RELEASE='release-20260806-intmain-head-test-r260806c-r1'
APP_HEAD='19173d2b41442e6b2df3c16c424c11713b3dbbcc'
errors=[]
checks={}
manifest_path=PKG/'manifest.json'
legacy_path=PKG/'release-manifest.json'
checks['packageDirExists']=PKG.exists()
checks['manifestExists']=manifest_path.exists()
checks['legacyManifestExists']=legacy_path.exists()
manifest={}
if manifest_path.exists():
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    checks['releaseTagMatches']=manifest.get('releaseTag')==RELEASE
    checks['componentIntruoyi']=(manifest.get('component')=='intruoyi' or (manifest.get('changeSet') or {}).get('component')=='intruoyi')
    checks['publishScopeCodeOnly']=manifest.get('publishScope')=='code-only'
    source=manifest.get('sourceRepos') or []
    checks['sourceReposPresent']=len(source)>0
    source_details=[]
    for repo in source:
        detail={k:repo.get(k) for k in ['name','pathRole','branch','commit','dirty','path']}
        detail['commitMatchesAppHead']=repo.get('commit')==APP_HEAD
        detail['dirtyFalse']=repo.get('dirty') is False
        source_details.append(detail)
    checks['allSourceCommitsMatch']=bool(source_details) and all(d['commitMatchesAppHead'] for d in source_details)
    checks['allSourceDirtyFalse']=bool(source_details) and all(d['dirtyFalse'] for d in source_details)
    artifacts=manifest.get('artifacts') or []
    mismatches=[]
    missing=[]
    for artifact in artifacts:
        rel=artifact.get('path') or artifact.get('relativePath') or artifact.get('file')
        if not rel:
            continue
        p=PKG/rel
        if not p.exists():
            missing.append(rel)
            continue
        expected=(artifact.get('sha256') or artifact.get('hash') or '').lower()
        if expected.startswith('sha256:'):
            expected=expected.split(':',1)[1]
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if expected and actual != expected:
            mismatches.append({'path':rel,'expected':expected,'actual':actual})
    checks['artifactsPresent']=len(artifacts)>0
    checks['artifactMissingCount']=len(missing)
    checks['artifactMismatchCount']=len(mismatches)
    checks['changeSetPresent']=bool((manifest.get('changeSet') or {}).get('summary') or (manifest.get('changeSet') or {}).get('changes'))
else:
    source_details=[]; artifacts=[]; missing=[]; mismatches=[]
release_info_path=Path(r'D:\IntRuoyiWorktree\r260806c-release-app\IntRuoyiFronted\dist-intruoyi-test\release-info.json')
checks['frontendReleaseInfoExists']=release_info_path.exists()
release_info={}
if release_info_path.exists():
    release_info=json.loads(release_info_path.read_text(encoding='utf-8'))
    checks['releaseInfoTagMatches']=release_info.get('releaseTag')==RELEASE
    ri_source=release_info.get('sourceRepos') or []
    checks['releaseInfoSourceDirtyFalse']=bool(ri_source) and all(repo.get('dirty') is False for repo in ri_source)
    checks['releaseInfoSourceCommitsMatch']=bool(ri_source) and all(repo.get('commit')==APP_HEAD for repo in ri_source)
    ri_changes=release_info.get('changeSet') or {}
    checks['releaseInfoChangeSetPresent']=bool(ri_changes.get('summary') or ri_changes.get('changes') or ri_changes.get('gitChanges'))
for key,value in checks.items():
    if key.endswith('Count'):
        if value != 0:
            errors.append(f'{key}={value}')
    elif value is not True:
        errors.append(f'{key}={value}')
result={
    'status':'passed' if not errors else 'failed',
    'releaseTag':RELEASE,
    'packageDir':str(PKG),
    'manifestPath':str(manifest_path),
    'legacyManifestPath':str(legacy_path),
    'frontendReleaseInfoPath':str(release_info_path),
    'checks':checks,
    'sourceRepos':source_details,
    'artifactCount':len(artifacts),
    'artifactMissing':missing,
    'artifactMismatches':mismatches,
    'changeSet':manifest.get('changeSet'),
    'releaseInfoChangeSet':release_info.get('changeSet'),
    'errors':errors,
}
(TASK/'manifest-validation-r260806c-r1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
summary={k:result[k] for k in ['status','releaseTag','packageDir','artifactCount','errors']}
summary['checks']=checks
summary['sourceRepos']=source_details
(TASK/'manifest-summary-r260806c-r1.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
if errors:
    raise SystemExit(1)
