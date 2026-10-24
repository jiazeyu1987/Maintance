"""Read-only SSH probe under the actual service account and environment."""
import json
import os
from pathlib import Path
import subprocess
import sys
import win32api
import win32serviceutil


def main():
    result = {'account': win32api.GetUserName(), 'checks': []}
    try:
        descriptor = Path(win32serviceutil.GetServiceCustomOption('IntRuoyiReleaseExecutor', 'Descriptor'))
        data = json.loads(descriptor.read_text('utf-8'))
        config_path = Path(sys.argv[2]) if len(sys.argv) == 3 else Path(data['config'])
        config = json.loads(config_path.read_text('utf-8-sig'))
        os.environ.update(data['environment'])
        source = descriptor.parent/'source/ops/spug/release-center'
        sys.path.insert(0, str(source))
        os.chdir(descriptor.parent/'source')
        from intruoyi_runtime import Runtime
        runtime = Runtime(config)
        for target in ('test', 'prod', 'backup'):
            process = subprocess.run(['ssh', *runtime.ssh_options(),
                'root@'+runtime.profile(target)['host'], 'true'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
            # The only remote command is true: no business/configuration output.
            result['checks'].append({'target': target, 'exit': process.returncode,
                'stderr': process.stderr.decode('utf-8', 'replace')[:4000]})
    except Exception as error:
        result['error'] = str(error)
    destination = Path(sys.argv[1])
    temporary = destination.with_suffix('.writing')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
    temporary.replace(destination)


if __name__ == '__main__':
    main()
