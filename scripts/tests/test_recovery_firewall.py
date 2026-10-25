"""Isolation ordering contracts, not live firewall acceptance."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))


def rule(chain, bridge):
    return [chain, '-i', bridge, *(['!', '-o', bridge] if chain == 'DOCKER-USER' else []),
            '-m', 'conntrack', '--ctstate', 'NEW,INVALID,UNTRACKED',
            '-m', 'comment', '--comment', 'recovery-' + 'a'*20, '-j', 'DROP']


@pytest.mark.parametrize('chain', ['INPUT', 'DOCKER-USER'])
def test_other_isolated_bridge_may_precede_target(chain):
    from recovery_firewall import isolation_rule_effective
    target = rule(chain, 'br-target')
    raw = '\n'.join(' '.join(['-A', *r]) for r in [rule(chain, 'br-other'), target])
    assert isolation_rule_effective(raw, target)


@pytest.mark.parametrize('prefix', [
    '-A INPUT -j ACCEPT', '-A INPUT -j RETURN', '-A INPUT -j UNKNOWN',
    '-A INPUT -i br+ -j DROP', '-A INPUT ! -i br-other -j DROP',
    '-A INPUT -i br-target -j ACCEPT',
])
def test_unknown_preceding_rule_rejected(prefix):
    from recovery_firewall import isolation_rule_effective
    target = rule('INPUT', 'br-target')
    assert not isolation_rule_effective(prefix + '\n' + ' '.join(['-A', *target]), target)


def test_target_must_exist_and_be_canonical():
    from recovery_firewall import isolation_rule_effective
    target = rule('INPUT', 'br-target')
    assert not isolation_rule_effective('-P INPUT ACCEPT', target)
    changed = [*target[:-1], 'ACCEPT']
    assert not isolation_rule_effective(' '.join(['-A', *changed]), changed)


def test_policy_and_rules_after_target_do_not_precede_it():
    from recovery_firewall import isolation_rule_effective
    target = rule('INPUT', 'br-target')
    assert isolation_rule_effective('-P INPUT ACCEPT\n' + ' '.join(['-A', *target]) + '\n-A INPUT -j ACCEPT', target)


def test_wildcard_bridge_is_not_a_disjoint_prefix():
    from recovery_firewall import isolation_rule_effective
    target = rule('INPUT', 'br-target')
    raw = '\n'.join(' '.join(['-A', *r]) for r in [rule('INPUT', 'br+'), target])
    assert not isolation_rule_effective(raw, target)
