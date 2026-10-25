"""Prove isolation despite other targets' exact, disjoint DROP prefixes."""
import re
import shlex


def _bridge(rule):
    if len(rule) < 3 or rule[0] not in ('INPUT', 'DOCKER-USER'):
        return None
    chain, _, bridge = rule[:3]
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,15}', bridge):
        return None
    prefix = [chain, '-i', bridge]
    if chain == 'DOCKER-USER':
        prefix += ['!', '-o', bridge]
    suffix = ['-m', 'conntrack', '--ctstate', 'NEW,INVALID,UNTRACKED',
              '-m', 'comment', '--comment']
    if (len(rule) != len(prefix) + len(suffix) + 3 or
            rule[:len(prefix)+len(suffix)] != prefix + suffix or
            not re.fullmatch(r'recovery-[0-9a-f]{20}', rule[-3]) or
            rule[-2:] != ['-j', 'DROP']):
        return None
    return bridge


def isolation_rule_effective(raw, target):
    """Unknown rules before the target remain a hard failure, never skipped."""
    bridge = _bridge(target)
    if bridge is None:
        return False
    try:
        for line in raw.splitlines():
            tokens = shlex.split(line)
            if not tokens:
                continue
            if (len(tokens) == 3 and tokens[:2] == ['-P', target[0]] and
                    tokens[2] in ('ACCEPT', 'DROP')):
                continue
            if tokens == ['-A', *target]:
                return True
            if (not tokens or tokens[0] != '-A' or len(tokens) < 2 or
                    tokens[1] != target[0]):
                return False
            preceding = _bridge(tokens[1:])
            if preceding is None or preceding == bridge:
                return False
    except ValueError:
        return False
    return False
