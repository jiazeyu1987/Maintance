"""Prepare task-owned local credentials without printing or committing secrets."""
import json
import argparse
import secrets
import subprocess
from pathlib import Path

PRIVATE = Path('E:/Int/CacheData/IntRuoyi/spug-integration-20261010')


def write_private(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Prepare only local private inputs; never select the latest package.')
    parser.add_argument('--backend-input', type=Path)
    parser.add_argument('--candidate-input', type=Path)
    args = parser.parse_args()
    PRIVATE.mkdir(parents=True, exist_ok=True)
    identity = subprocess.check_output(['whoami'], text=True).strip()
    subprocess.run(['icacls', str(PRIVATE), '/inheritance:r', '/grant:r', identity + ':(OI)(CI)F',
                    '*S-1-5-18:(OI)(CI)F'], capture_output=True, check=True)
    admin = PRIVATE / 'admin.private.json'
    if not admin.exists():
        admin.write_text(json.dumps({'username': 'admin', 'password': secrets.token_urlsafe(24)}, indent=2), encoding='utf-8')
    env = PRIVATE / 'compose.private.env'
    if not env.exists():
        env.write_text('SPUG_DB_PASSWORD=' + secrets.token_hex(24) + '\nSPUG_DB_ROOT_PASSWORD=' + secrets.token_hex(24)
                       + '\nSPUG_PRIVATE_DIR=' + PRIVATE.as_posix() + '\n', encoding='utf-8')
    config_path = PRIVATE / 'backend.private.json'
    if not config_path.exists():
        if not args.backend_input:
            raise SystemExit('BACKEND_INPUT_REQUIRED: provide a real private backend configuration; no default credentials.')
        source = json.loads(args.backend_input.read_text(encoding='utf-8-sig'))
        config = {k: source[k] for k in ('baseUrl', 'tenantId', 'username', 'password')}
        config.update(publishEnabled=False, productionPaused=True, allowedTargets=['TEST', 'BACKUP', 'PROD'])
        write_private(config_path, config)
    candidate_path = PRIVATE / 'candidate.private.json'
    if not candidate_path.exists():
        from release_adapter import BINDINGS, validate_selection
        if args.candidate_input:
            selection = json.loads(args.candidate_input.read_text(encoding='utf-8-sig'))
        else:
            # One-time migration preserves the existing explicit historical binding. No new candidate is chosen.
            config = json.loads(config_path.read_text(encoding='utf-8-sig'))
            if not all(k in config for k in BINDINGS):
                raise SystemExit('CANDIDATE_INPUT_REQUIRED: provide an explicitly selected existing immutable candidate.')
            selection = {k: config[k] for k in BINDINGS}
        write_private(candidate_path, validate_selection(selection))
    print('Private credentials prepared outside repository; ACL limited to current user and SYSTEM.')

if __name__ == '__main__':
    main()
