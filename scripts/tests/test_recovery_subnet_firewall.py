"""Minimal target subnet isolation must remain effective with other targets."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))


def rule(chain, subnet):
    return [chain, '-s', subnet, *(['!', '-d', subnet] if chain == 'DOCKER-USER' else []),
            '-m', 'conntrack', '--ctstate', 'NEW', '-j', 'REJECT',
            '--reject-with', 'icmp-port-unreachable']


def render(*rules):
    return '\n'.join(' '.join(['-A', *r]) for r in rules)


@pytest.mark.parametrize('chain', ['INPUT', 'DOCKER-USER'])
def test_disjoint_isolated_subnets_may_precede_target(chain):
    from recovery_firewall import subnet_isolation_rule_effective
    target = rule(chain, '172.28.146.0/24')
    raw = render(rule(chain, '172.28.150.0/24'), rule(chain, '172.28.149.0/24'), target)
    assert subnet_isolation_rule_effective(raw, target)


@pytest.mark.parametrize('chain', ['INPUT', 'DOCKER-USER'])
@pytest.mark.parametrize('subnet', ['172.28.0.0/16', '172.28.146.0/24', '172.28.146.128/25'])
def test_overlapping_prefix_is_not_accepted(chain, subnet):
    from recovery_firewall import subnet_isolation_rule_effective
    target = rule(chain, '172.28.146.0/24')
    prefix = rule(chain, subnet)
    # An identical rule is itself already the effective target.
    if prefix == target:
        prefix[-1] = 'icmp-host-unreachable'
    assert not subnet_isolation_rule_effective(render(prefix, target), target)


@pytest.mark.parametrize('prefix', [
    '-A INPUT -j ACCEPT', '-A INPUT -j RETURN', '-A INPUT -j CUSTOM',
    '-A INPUT -s 172.28.149.0/24 -j ACCEPT', '-P INPUT QUEUE',
    '-A DOCKER-USER -j RETURN', '-A INPUT "',
])
def test_unknown_prefix_fails_closed(prefix):
    from recovery_firewall import subnet_isolation_rule_effective
    target = rule('INPUT', '172.28.146.0/24')
    assert not subnet_isolation_rule_effective(prefix + '\n' + render(target), target)


@pytest.mark.parametrize('subnet', ['172.28.146.1/24', '::/0', 'not-a-network'])
def test_noncanonical_target_rejected(subnet):
    from recovery_firewall import subnet_isolation_rule_effective
    target = rule('INPUT', subnet)
    assert not subnet_isolation_rule_effective(render(target), target)


def test_target_presence_and_suffix():
    from recovery_firewall import subnet_isolation_rule_effective
    target = rule('INPUT', '172.28.146.0/24')
    assert not subnet_isolation_rule_effective('-P INPUT ACCEPT', target)
    assert subnet_isolation_rule_effective('-P INPUT ACCEPT\n' + render(target) + '\n-A INPUT -j ACCEPT', target)


def test_docker_destination_must_match_source():
    from recovery_firewall import subnet_isolation_rule_effective
    target = rule('DOCKER-USER', '172.28.146.0/24')
    other = rule('DOCKER-USER', '172.28.149.0/24')
    other[5] = '172.28.0.0/16'
    assert not subnet_isolation_rule_effective(render(other, target), target)


def test_actual_user_chain_declaration_is_not_a_rule():
    from recovery_firewall import subnet_isolation_rule_effective
    target = rule('DOCKER-USER', '172.28.146.0/24')
    assert subnet_isolation_rule_effective('-N DOCKER-USER\n' + render(target), target)
    assert not subnet_isolation_rule_effective('-N OTHER\n' + render(target), target)
