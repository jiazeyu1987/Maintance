"""Explicit read-only rehearsal dependency/schema inspection; never prepares resources."""
import argparse
import hashlib
import json
from pathlib import Path

from intruoyi_runtime import Runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--check', choices=('media-inventory', 'media-column-proof', 'writer-inventory', 'target-check'), required=True)
    arguments = parser.parse_args()
    runtime = Runtime(json.loads(arguments.config.read_text('utf-8')))
    if arguments.check == 'target-check':
        result = runtime.call('rehearsal', 'rehearsal-target-check', sourceProfile=runtime.profile(arguments.source))
    else:
        result = runtime.call(arguments.source, 'rehearsal-' + arguments.check)
    content = json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')
    # Keep the operator's previous evidence; output must be an explicitly new file.
    with arguments.output.open('xb') as stream:
        stream.write(content)
    print(json.dumps({'check': arguments.check, 'mutations': False,
                      'evidenceSha256': hashlib.sha256(content).hexdigest(),
                      'output': str(arguments.output.resolve())}))


if __name__ == '__main__':
    main()
