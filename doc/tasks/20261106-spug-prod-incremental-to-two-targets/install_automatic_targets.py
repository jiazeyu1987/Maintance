"""Review-first installer for the two remaining existing MAIN restore controls.

Default/--prepare-only performs local package/configuration checks only. The
remote installer is dispatched only with --activate and one explicit target.
"""
import argparse
import base64
import hashlib
import json

from common import TASK, PRIVATE, SOURCE, remote, write
from automatic_targets_install_script import SCRIPT, GATE, SOURCE_IDLE
from installation_history_custody import SCRIPT as CUSTODY_SCRIPT
from plan_automatic_targets import COMMIT, candidate, verified_package, extend_verified_custody
from automatic_target_finalize_script import finalization_script
from automatic_target_epoch_resume import load_epoch_resume_proof


def prepare(suffix):
    build, files = verified_package()
    generated = candidate(suffix, build, files)
    private_path = PRIVATE / ('automatic-target-candidate-' + suffix + '-0d44578.private.json')
    if private_path.exists():
        assert json.loads(private_path.read_text(encoding='utf-8')) == generated, 'CANDIDATE_REVIEW_INPUT_CHANGED'
    else:
        write(private_path, generated)
    compile(CUSTODY_SCRIPT + '\n' + SCRIPT, '<target-installer>', 'exec')
    compile(GATE, '<target-constructor-gate>', 'exec')
    compile(SOURCE_IDLE, '<target-source-idle>', 'exec')
    compile(finalization_script(), '<target-finalize-activated>', 'exec')
    return generated, build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target', nargs='?', choices=('58', '59'))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare-only', action='store_true')
    mode.add_argument('--activate', action='store_true')
    mode.add_argument('--finalize-activated', action='store_true')
    parser.add_argument('--resume-staged', action='store_true')
    parser.add_argument('--resume-epoch-stage', action='store_true')
    args = parser.parse_args()
    if args.activate and args.target is None:
        parser.error('--activate requires exactly one target')
    if args.resume_staged and not (args.activate and args.target=='58'):
        parser.error('--resume-staged requires 58 --activate and the retained failed-attempt proof')
    if args.resume_epoch_stage and not (args.activate and args.target=='59' and not args.resume_staged):
        parser.error('--resume-epoch-stage requires 59 --activate and the exact empty-epoch-stage proof')
    if args.finalize_activated and args.target!='58':
        parser.error('--finalize-activated requires the exact already activated target 58')
    for suffix in (args.target,) if args.target else ('58', '59'):
        selected, build = prepare(suffix)
        if not (args.activate or args.finalize_activated):
            print(json.dumps(dict(status='PREPARED_NOT_DEPLOYED', host=selected['host'],
                sourceCommit=COMMIT, fileCount=130, oldControlPid=selected['oldControlPid'],
                ownerConfigurationPin=selected['ownerConfigurationPin'],
                controlConfigurationPin=selected['controlConfigurationPin'],
                epochStatus=selected['epochStatus'], remoteCalls=0, serverWrites=False)))
            continue
        output = TASK / ('automatic-target-installation-' + suffix + '.json')
        assert not output.exists(), 'INSTALLATION_ALREADY_RECORDED'
        epoch_pins = []
        if suffix == '59':
            evidence = json.loads((PRIVATE / 'automatic-target-epoch-59-binding.private.json').read_text(encoding='utf-8'))
            epoch_pins = [row['capturePin'] for row in evidence['rows']]
        raw = (PRIVATE / 'package-0d44578/backup-restore-standard.tgz').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == build['packageSha256']
        resume_proof=None
        if args.resume_staged:
            resume_proof=json.loads((TASK/'automatic-target58-failed-activation-diagnosis.json').read_text(encoding='utf-8'))
            assert resume_proof['serverWrites'] is False and resume_proof['originalAttemptTreeSnapshotUnavailable'] is True
            assert resume_proof['allRetainedOriginalPinsMatch'] and not resume_proof['newDropins']
        history_code=(TASK/'automatic_target_history_guard.py').read_text(encoding='utf-8')
        readiness_code=(TASK/'automatic_target_http_ready.py').read_text(encoding='utf-8')
        runtime_code=(TASK/'automatic_target_runtime_contract.py').read_text(encoding='utf-8')
        epoch_code=(TASK/'automatic_target_epoch_initializer.py').read_text(encoding='utf-8')
        epoch_resume_code=(TASK/'automatic_target_epoch_resume.py').read_text(encoding='utf-8')
        epoch_resume_proof=load_epoch_resume_proof(TASK/'automatic-target59-empty-epoch-resume-proof.json') if args.resume_epoch_stage else None
        variables = dict(COMMIT=COMMIT, SUFFIX=suffix, SOURCE=SOURCE, CANDIDATE=selected,
            EPOCH_CAPTURE_PINS=epoch_pins, PACKAGE=base64.b64encode(raw).decode(), GATE=GATE,
            SOURCE_IDLE=SOURCE_IDLE,RESUME_STAGED=args.resume_staged,RESUME_PROOF=resume_proof,
            RESUME_EPOCH_STAGE=args.resume_epoch_stage,EPOCH_RESUME_PROOF=epoch_resume_proof)
        body=SCRIPT
        if args.finalize_activated:
            variables['FINALIZE_PROOF']=json.loads((TASK/'automatic-target58-resume-activation-failure.json').read_text(encoding='utf-8'))
            body=finalization_script()
        script = '\n'.join(key + '=' + repr(value) for key, value in variables.items()) + '\n' + history_code + '\n' + readiness_code + '\n' + runtime_code + '\n' + epoch_code + '\n' + epoch_resume_code + '\n' + CUSTODY_SCRIPT + '\n' + body
        result = remote(selected['host'], script, timeout=900)
        assert result['status'] == 'PASS'
        extended = extend_verified_custody(selected['previousCustody'], result, selected)
        assert result['extendedCustody'] == extended
        private_result = PRIVATE / ('automatic-target-installation-' + suffix + '.private.json')
        assert not private_result.exists(), 'PRIVATE_INSTALLATION_ALREADY_RECORDED'
        write(private_result, result)
        # The public receipt contains metadata and hashes, never control/env values.
        write(output, result)
        write(TASK / ('automatic-target-installation-custody-' + suffix + '.json'), extended)
        print(json.dumps({key: result[key] for key in ('status', 'host', 'service', 'sourceCommit',
            'controlPid', 'epochStatus', 'targetAndSourceConfigurationUnchanged',
            'allBusinessDefinitionsAndRuntimeUnchanged', 'restoreDispatched', 'backupDispatched')}))


if __name__ == '__main__':
    main()
