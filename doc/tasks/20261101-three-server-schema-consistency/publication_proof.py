"""Validate the original build or its linked, successful same-package publication."""
def verify_publication(state, candidate, package):
    build = next(j for j in state['jobs'] if j['id'] == candidate['buildJobId'])
    assert build['action'] == 'build-release'
    assert build['releaseTag'] == candidate['releaseTag'] == package['releaseTag']
    assert build['payload']['commit'] == candidate['sourceCommit'] == package['gitCommit']
    if build['status'] == 'succeeded':
        return build
    assert build['status'] == 'failed' and not build.get('effectsStarted')
    retry = next(j for j in state['jobs'] if j['id'] == candidate['packagePublicationJobId'])
    assert retry['status'] == 'succeeded' and retry['action'] == 'resolve-task'
    assert retry['releaseTag'] == candidate['releaseTag']
    assert retry['payload']['decision'] == 'retry'
    assert retry['originalBuildJobId'] == retry['result']['originalBuildJobId'] == build['id']
    assert retry['result']['packageSha256'] == package['packageSha256'] == build['sealedPackage']['packageSha256']
    assert build['resolution']['decision'] == 'retry' and build['resolution']['jobId'] == retry['id']
    assert build['buildWorktreeCleanup']['status'] == 'passed'
    return build
