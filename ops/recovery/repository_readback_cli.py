"""Independent SMB readback only; never reports a restore as executed."""
import argparse
import sys

from repository_minimal import execute
from repository_records import RepositoryError


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('configuration', 'request', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    return execute(args.configuration, args.request, args.output, readback_only=True)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(error.code if isinstance(error, RepositoryError) else 'REPOSITORY_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(2 if isinstance(error, RepositoryError) and error.unknown else 1)
