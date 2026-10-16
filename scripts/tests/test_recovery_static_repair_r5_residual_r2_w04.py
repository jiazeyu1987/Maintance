"""Local W03 publication-contract graph through the actual W04 CLI; no native execution."""
import base64
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption, PublicFormat

from test_recovery_static_repair_r5_residual_w04 import signed_cli
import recovery_cli as cli
from recovery_engine import canonical, load, pin, write


@pytest.fixture
def publication_cli(signed_cli, request):
    options = getattr(request, 'param', {})
    configure, external = signed_cli
    root = external.parent
    provenance = root/'provenance'; provenance.mkdir(mode=0o700)
    key = Ed25519PrivateKey.generate()
    public = provenance/'native.pem.recording-failure.json'
    public.write_bytes(key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    private = provenance/'signing.pem'
    private.write_bytes(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
    program = provenance/'harmless.py.recording-failure.json'; program.write_bytes(b'raise SystemExit(0)\n')
    dependency = provenance/'dependency.py.recording-failure.json'; dependency.write_bytes(b'VALUE = 1\n')
    # Peer.acquire requires at least one exact byte custody Pin. Keep this
    # original outside sourceRoots so the field classification owns exclusion.
    custody = external/'custody.bin.recording-failure.json'; custody.write_bytes(b'\x00native-custody\xff')
    byte_pins = dict(nativeAuthorityKeyPins=pin(public), evidenceSigningKeyPin=pin(private),
                     programPin=pin(program), nativeDependencyPins=pin(dependency), netExePin=pin(Path(sys.executable)),
                     custodyPaths=pin(custody))
    def document(name, **value): return write(provenance/(name+'.json'), value)
    def signed(name, payload):
        return document(name, schemaVersion='RepositorySignedRecord/v1', keySha256=pin(public)['sha256'],
                        payload=payload, signature=base64.b64encode(key.sign(canonical(payload))).decode())
    identity = document('identity', sourceId='local-contract-engineering')
    view = document('view', schemaVersion='RepositoryHostView/v1',
                    mappings=[dict(originalPrefix=str(provenance), localPrefix=str(provenance))])
    # Same complete field contracts as repository_records.Configuration,
    # repository_native_peer.PeerConfiguration and repository_wsl_carrier.
    registration = document('registration', schemaVersion='RecoveryLocalEnvironmentRegistration/v1',
                            usableForExecution=True, host={'selectedExecutionHost':'local-contract-only'})
    host = document('host', schemaVersion='RecoveryControlExecutionHost/v1', transport='WSL', hostOs='Linux',
        hostId='engineering-host', bootId='engineering-boot', uid=0, sourceProfilePin=registration,
        pythonPin=pin(Path(sys.executable)), dispatcherPin=pin(program), scriptPin=pin(program),
        workingDirectory=str(provenance), evidenceRoot=str(provenance), launcherPin=pin(program),
        launcherArguments=['--distribution','engineering','--user','root','--exec'], environment={},
        resourceObserverPin=pin(dependency))
    template_original = document('template-original', engineeringOnly=True)
    credential = document('credential', schemaVersion='RepositorySmbCredential/v1', server='engineering',
                          share='engineering', username='engineering', password='non-operative-local-fixture')
    catalog_material = document('catalog-material', schemaVersion='backup-capture-materials/v1', files=[pin(program)])
    material_index = document('material-index', schemaVersion='backup-capture-material-index/v1',
                              files=[dict(archivePath='tool.bin', sourcePin=pin(program), purpose='tools')])
    object_inventory = provenance/'object-inventory.jsonl'; object_inventory.write_bytes(b'')
    catalog = document('catalog', schemaVersion='backup-capture-catalog/v1',
                       assets=[dict(assetId='tools', **{'class':'tools'}, policy='CAPTURE', reference=catalog_material)])
    series = document('series', schemaVersion='backup-capture-series/v1', backupId='engineering',
                      generationId='engineering', pointType='FULL', catalogPin=catalog,
                      parentPointPin=None, parentRepositoryPointPin=None)
    assembly_documents = ('sourceReferencesPin bootSourcesPin bootConnectionsPin controlledSourcesPin '
                          'resumeRequestPin captureRequestPin recoveryFlowsPin catalogBindingPin channelPin').split()
    assembly = document('assembly', schemaVersion='backup-normal-owner-assembly/v1', binding={},
        programPin=pin(program), inputReferences={name:template_original for name in
            ('policy source_context installed_context release_binding coverage allocation source_guard staging_admission').split()} |
            {'archive_program':pin(program),'mysql_credential':credential}, controlRoot=str(provenance),
        registryRoot=str(provenance), maintenanceMilliseconds=30000, seriesPin=series,
        **{name:template_original for name in assembly_documents})
    recipe = document('recipe', schemaVersion='backup-normal-owner-recipe/v1', action='serve-approved-backup-owner',
        totalSeconds=30, attribution={}, executionContractPin=template_original, creationResultsPin=template_original,
        claimRoot=str(provenance), claimBinding={}, nativeAssemblyProgramPin=pin(program), nativeAssemblyConfigPin=assembly)
    proof = document('source-proof', path=str(provenance), device=0, inode=0)
    peer_roles = ('records catalog retention cli nativeBridge installerProgram publishProgram binding '
                  'nativePeer nativeReadback hostView wslCarrier wslDispatcher').split()
    peer = signed('peer', dict(schemaVersion='RepositoryNativePeerConfig/v1', repositoryId='engineering',
        sourceIdentityPin=identity, programPin=pin(program), ownerPythonPin=pin(Path(sys.executable)),
        ownerEntryPin=pin(program), ownerDependencyPins=[pin(dependency)], recipeTemplatePin=recipe,
        assemblyTemplatePin=assembly, sessionRoot=str(provenance), custodyPaths=[pin(custody)], resourceRoots={},
        sourceRoots=[str(provenance)], sourceRootProofPins=[proof], writerContainers=[], dockerPin=pin(program),
        nftPin=pin(program), writerRulesSha256='a'*64, readbackConfig=dict(uncRoot='engineering',
            repositoryRelativePath='engineering', repositoryRoot=str(provenance), credentialPin=credential,
            port=445, authProtocol='ntlm', recordRoot=str(provenance), maximumRecordBytes=1024,
            maximumTotalRecordBytes=4096, libraryPins=[pin(dependency)], schemaVersion='RepositorySmbReadbackConfig/v1'),
        signingKeyPin=pin(private), nativeImplementationPins={role:pin(program) for role in peer_roles}, hostViewPin=view))
    policy = signed('repository-policy', dict(schemaVersion='RepositoryPolicy/v1', repositoryId='engineering',
        sourceIdentityPin=identity, supportedVersionPins=[pin(program)], supportedToolPins=[pin(program)],
        maxChainPoints=16, maxChainAgeSeconds=300, retainNewestPoints=1, minValidFullPoints=1,
        retentionSeconds=300, legalHoldPointPins=[], copyProtectionPin=recipe))
    service_roles = peer_roles + ['publisherModule','interfaceModule','deploymentEvidenceModule','captureBinder']
    service = document('service', schemaVersion='RepositoryServiceConfig/v1', repositoryId='engineering',
        repositoryRoot=str(provenance), evidenceRoot=str(provenance), schemaPin=pin(program), policyPin=policy,
        authorityKeyPins=[pin(public)], evidenceKeyPins=[pin(public)], publisherPin=pin(program),
        powershellPin=pin(program), installerPin=pin(program), implementationPins={role:pin(program) for role in service_roles},
        captureBinderDependencyPins=[pin(dependency)], recoveryApprovalPins=[], hostViewPin=view)
    carrier = document('carrier', schemaVersion='RepositoryWslCarrierConfig/v1', executionHostPin=host,
        windowsHostViewPin=view, nativeHostViewPin=view, nativeServiceConfigurationPin=service,
        nativePeerConfigurationPin=peer, nativeDependencyPins=[pin(program),pin(dependency)])
    request = document('prepare', schemaVersion='backup-restore-operation/v1', operationId='engineering',
        requestId='engineering', action='BACKUP_FULL', mode='REHEARSAL', selectedPointPin=None,
        sourceOrTargetRef=recipe, policyPin=policy, authorizationRefs=[], leaseRef=recipe, inputPins={},
        deadlineMilliseconds=30000)
    command = dict(schemaVersion='RepositoryNativeCommand/v1', executablePin=pin(Path(sys.executable)),
                   programPins=[pin(program),pin(dependency)], arguments=['-B',str(program)], workingDirectory=str(provenance))
    # Exact RepositoryBackupSource/v1 field list from repository_installer.preflight.
    source = document('source', schemaVersion='RepositoryBackupSource/v1', repositoryId='engineering',
        sourceIdentityPin=identity, pythonPin=pin(Path(sys.executable)), netExePin=pin(Path(sys.executable)),
        ownerCommand=command, nativeVerifierCommand=command, nativeAuthorityKeyPins=[pin(public)],
        nativePeerConfigPin=peer, bootstrapBinding={'nasWorkspaceConfigSha256':recipe['sha256']},
        baseSchemaPin=pin(program), controlAddendumPin=pin(dependency), workspacePin=recipe,
        workspaceDirectory=str(provenance), workspaceOwnerSid='engineering', localStagingRoot=str(provenance),
        localRootCreationTicks=1, nasCredentialPin=credential, nasReleaseRoot='engineering',
        approvedNasRoot='engineering', evidenceSigningKeyPin=pin(private), prepareRequestPin=request,
        captureRequestPin=request, hostViewPin=view, wslCarrierConfigPin=carrier)
    native_request = document('native-request', schemaVersion='RepositoryNativeRequest/v1', action='observe-readback',
        challenge='engineering', request={'operationRequestPin':request}, sourceConfigPin=source, remainingMilliseconds=30000)
    response = signed('native-response', dict(schemaVersion='RepositoryNativeResponse/v1', challenge='engineering',
        action='observe-readback', sourceConfigPin=source, requestPin=native_request,
        result={'state':'READBACK','originalRecordsPin':recipe}))
    capture_request = document('native-capture-request', schemaVersion='RepositoryNativeRequest/v1',
        action='observe-capture', challenge='capture', request={'operationRequestPin':request},
        sourceConfigPin=source, remainingMilliseconds=30000)
    # Mirror the selected producers, without executing the native owner:
    # FixedManifest serializes the entries map; run_owner writes the recovery
    # receipt/header; Peer observe-capture returns these exact document Pins.
    # All three direct originals are deliberately outside sourceRoots.
    originals = external/'capture-originals'; originals.mkdir(mode=0o700)
    def capture_document(name, value):
        path = originals/(name+'.json.recording-failure.json')
        path.write_bytes(b'not-json' if options.get('invalid_json') == name else canonical(value))
        return pin(path)
    entries = {'payload':'directory', 'payload/tool.bin':f"file|{pin(program)['bytes']}|{pin(program)['sha256']}"}
    manifest = capture_document('manifest', entries)
    point = capture_document('capture-point', dict(schemaVersion='backup-capture-point/v1',
        backupId='engineering',generationId='engineering',pointType='FULL',sourceIdentity={'sourceId':'engineering'},
        catalogPin=catalog,parentPointPin=None,parentRepositoryPointPin=None,
        databaseEnd={'databaseUuid':'engineering','file':'binlog.000001','position':4},
        databaseDelta={'kind':'SQL_FULL','segments':[]},fileInventory={},
        fileDelta={'changedPaths':[],'deletedPaths':[]},sourceRestored=True,disasterRecoveryVerified=False,
        commonRecoveryPoint='sha256:'+'a'*64))
    recovery = capture_document('original-recovery', dict(
        state='A_ORIGINAL_CAPTURE_AND_RECOVERY_COMPLETED_PENDING_NAS',
        sharedCapture=dict(state='A_SHARED_CAPTURED_AND_ORIGINAL_SERVICES_RESTORED_PENDING_REMAINING_OWNER',
            capture={},restoration={},ingressRulesSha256='a'*64,originalConfigs={},originalImages={},
            capturedPayloadEntries=entries,capturedArchiveEntries=entries,
            productionEvidence=False,fullRunnerCompleted=False,releaseReady=False,claimReleased=False),
        originalParticipants=dict(state='ORIGINAL_PARTICIPANTS_RESTORED_INGRESS_RELEASED_PENDING_NAS',
            sharedHealth={},externalHealth={},hostEntries=[],ingress={},productionEvidence=False,
            releaseReady=False,fullRunnerCompleted=False,claimReleased=False,nasArchiveVerified=False),
        productionEvidence=False,releaseReady=False,fullRunnerCompleted=False,claimReleased=False,nasArchiveVerified=False))
    receipt_value = dict(state='SOURCE_RESTORED_PENDING_NAS',sourceRestored=True,
        disasterRecoveryVerified=False,capturePointReference=point,originalRecoveryReference=recovery)
    if options.get('unknown_reference') == 'receipt': receipt_value['unclassifiedReceiptReference'] = recipe
    receipt = capture_document('recovery-receipt', receipt_value)
    binding = {name:'a'*64 for name in ('attemptId sourceContextSha256 installedContextSha256 '
        'originalReleaseBindingSha256 claimBindingSha256 approvedSourceTargetSha256 capturePolicySha256 '
        'nasWorkspaceConfigSha256').split()} | {'releaseTag':'engineering'}
    header_value = dict(schemaVersion='release-production-backup-archive-header/v1',binding=binding,
        manifestReference=manifest,treeDigest='a'*64,fileCount=1,totalBytes=pin(program)['bytes'],
        recoveryReceiptReference=receipt,archiveRemainingBudget=dict(remainingMilliseconds=30000,observationReference=receipt))
    if options.get('unknown_reference') == 'header': header_value['unclassifiedHeaderReference'] = recipe
    header = capture_document('archive-header', header_value)
    metadata = dict(schemaVersion='RepositoryCaptureMetadata/v1',backupId='engineering',generationId='engineering',
        pointType='FULL',parentPointPins=[],commonRecoveryPoint='sha256:'+'a'*64,sourceIdentityPin=identity,
        createdAt='2026-10-11T00:00:00Z',versionPins=[pin(program)],toolPins=[pin(program)])
    observation = document('capture-observation',schemaVersion='RepositoryNativeCaptureObservation/v1',
        ownerIdentity={'pid':1,'engineeringOnly':True},archiveHeaderPin=header,at='2026-10-11T00:00:00Z')
    capture_response = signed('native-capture-response', dict(schemaVersion='RepositoryNativeResponse/v1',
        challenge='capture', action='observe-capture', sourceConfigPin=source, requestPin=capture_request,
        result=dict(schemaVersion='RepositoryNativeCapture/v1',repositoryId='engineering',operationId='engineering',
            requestPin=request,sourceConfigPin=source,binding=binding,originalProcessPin=template_original,
            archiveHeaderPin=header,payloadTree=entries,metadata=metadata,nativeEvidencePins=[observation])))
    fixture = configure(external/'original.json', {
        'ownerCloseEvidencePin':{'nativeCaptureResponsePin':capture_response},
        'readbackEvidencePin':{'nativeResponsePin':response}})
    fixture.document_pins = dict(source=source, peer=peer, carrier=carrier, host=host, native_response=response,
                                 recipe=recipe,assembly=assembly,archive_header=header,manifest=manifest,
                                 recovery_receipt=receipt,capture_point=point,original_recovery=recovery,
                                 native_capture_response=capture_response)
    fixture.byte_pins = byte_pins
    return fixture


def test_actual_publication_byte_graph_preflight_and_three_cache_destinations(publication_cli):
    fixture = publication_cli
    originals = {ref['path']:Path(ref['path']).read_bytes() for ref in fixture.byte_pins.values()}
    output = fixture.root/'safe-publication.json'
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 0
    result = load(output)
    assert result['state'] == 'SUCCEEDED'
    assert result['data']['orderedChainPins'] == [fixture.request['selectedPointPin']]
    journal = next(fixture.evidence.glob('request-*.json')); journal_bytes = journal.read_bytes()
    for destination in (output,fixture.root/'new-publication.json',fixture.evidence/'public.json'):
        assert cli.main(['--request',fixture.request_pin['path'],'--output',str(destination)]) == 0
        assert load(destination) == result and journal.read_bytes() == journal_bytes
    assert all(Path(path).read_bytes() == raw for path,raw in originals.items())
    assert not fixture.invocations and not list(fixture.evidence.glob('operation-*/invocation-*'))


@pytest.mark.parametrize('kind',['nativeAuthorityKeyPins','programPin','nativeDependencyPins'])
@pytest.mark.parametrize('destination',['primary','secondary'])
def test_actual_publication_byte_leaf_is_protected(publication_cli, kind, destination, capsys):
    fixture = publication_cli
    original = Path(fixture.byte_pins[kind]['path']); retained = original.read_bytes()
    output = original if destination == 'primary' else original.with_name('public.json')
    if destination == 'secondary':
        output = original.with_name(original.name.removesuffix('.recording-failure.json'))
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 1
    assert original.read_bytes() == retained and not fixture.invocations
    assert not list(fixture.evidence.iterdir())
    assert 'PUBLIC_OUTPUT_PROTECTED_PATH' in capsys.readouterr().out


@pytest.mark.parametrize('kind',['source','peer','carrier','host','native_response'])
@pytest.mark.parametrize('fault',['missing','changed'])
def test_actual_publication_document_scope_failure_never_publishes(publication_cli, kind, fault, capsys):
    fixture = publication_cli
    document = Path(fixture.document_pins[kind]['path'])
    if fault == 'missing': document.unlink()
    else: document.write_bytes(document.read_bytes()+b' ')
    output = fixture.root/'safe-publication.json'
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 1
    assert not output.exists() and not output.with_name(output.name+'.recording-failure.json').exists()
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    assert 'PUBLIC_OUTPUT_SCOPE_INCOMPLETE' in capsys.readouterr().out


def test_unknown_reference_type_keeps_scope_incomplete(publication_cli, capsys):
    fixture = publication_cli
    fixture.request['unclassifiedEvidencePin'] = fixture.document_pins['source']
    # Exercise collect directly with the actual admitted graph; frozen request
    # schema rejection is a separate gate and must not mask unknown Pin typing.
    from recovery_plan import trusted_configuration
    from recovery_engine import Budget, RecoveryError
    trust,policy,config = trusted_configuration(load(fixture.request_pin['path']))
    publisher = cli.PublicOutput(fixture.root/'safe-publication.json')
    with pytest.raises(RecoveryError, match='PUBLIC_OUTPUT_SCOPE_REFERENCE_TYPE_UNKNOWN'):
        publisher.bind(fixture.request,fixture.request_pin,trust,policy,config,Budget(30000))
    assert not publisher.complete and Path(fixture.document_pins['source']['path']) in publisher.protected
    assert not Path(publisher.path).exists() and not fixture.invocations
