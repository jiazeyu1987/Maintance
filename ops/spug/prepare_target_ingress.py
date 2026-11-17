"""Persistent HTTP ingress for the fixed network in an empty-target configuration.

Docker internal networks do not expose their published ports. Keep recovery
containers unchanged and let the host's existing socket proxy reach the frontend.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import subprocess


UNIT = 'spug-recovery-frontend'
MARKER = '# Managed by prepare_target_ingress.py\n'
PROXY = '/usr/lib/systemd/systemd-socket-proxyd'


def render(config, port):
    host = str(ipaddress.IPv4Address(config['host']))
    network = ipaddress.IPv4Network(config['subnet'])
    roles = [service['role'] for service in config['services']]
    if roles.count('frontend') != 1 or not 1 <= port <= 65535:
        raise ValueError('One frontend and a valid public port are required')
    upstream = network.network_address + 32 + roles.index('frontend')
    if upstream not in network or upstream == network.broadcast_address:
        raise ValueError('Frontend is outside the preparation subnet')
    socket = MARKER + (
        '[Unit]\nDescription=Restored application public HTTP socket\n'
        '[Socket]\nListenStream=' + host + ':' + str(port) + '\nNoDelay=true\nFreeBind=true\n'
        '[Install]\nWantedBy=sockets.target\n')
    service = MARKER + (
        '[Unit]\nDescription=Restored application frontend proxy\n'
        'Requires=' + UNIT + '.socket\nAfter=' + UNIT + '.socket docker.service\n'
        '[Service]\nExecStart=' + PROXY + ' ' + str(upstream) + ':80\n'
        'User=nobody\nNoNewPrivileges=true\nPrivateTmp=true\n'
        'ProtectSystem=full\nProtectHome=true\n')
    rule = ('rule family="ipv4" destination address="' + host + '/32" '
            'port port="' + str(port) + '" protocol="tcp" accept')
    return dict(socket=socket, service=service, firewallRule=rule,
                url='http://' + host + ':' + str(port), upstream=str(upstream))


def install(plan):
    if not Path(PROXY).is_file():
        raise FileNotFoundError(PROXY)
    units = {suffix: Path('/etc/systemd/system') / (UNIT + '.' + suffix)
             for suffix in ('socket', 'service')}
    for path in units.values():
        if path.exists() and not path.read_text(encoding='utf-8').startswith(MARKER):
            raise ValueError('Existing unit is not owned by this installer: ' + str(path))
    for suffix, path in units.items():
        path.write_text(plan[suffix], encoding='utf-8')
        path.chmod(0o644)
    def run(*args):
        subprocess.run(args, check=True, timeout=30)
    run('systemd-analyze', 'verify', *(str(path) for path in units.values()))
    run('systemctl', 'daemon-reload')
    run('systemctl', 'stop', UNIT + '.service', UNIT + '.socket')
    run('systemctl', 'enable', UNIT + '.socket')
    run('systemctl', 'start', UNIT + '.socket')
    run('systemctl', 'is-active', UNIT + '.socket')
    # Preserve all other firewall rules; this opens only the declared HTTP entry.
    run('firewall-cmd', '--permanent', '--zone=public', '--add-rich-rule=' + plan['firewallRule'])
    run('firewall-cmd', '--zone=public', '--add-rich-rule=' + plan['firewallRule'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='Installed empty-target preparation configuration')
    parser.add_argument('--port', type=int, default=8081)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    plan = render(json.loads(Path(args.config).read_text(encoding='utf-8')), args.port)
    if args.apply:
        install(plan)
    print(json.dumps(plan))


if __name__ == '__main__':
    main()
