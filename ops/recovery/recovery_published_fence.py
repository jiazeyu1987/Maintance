"""Operation-owned host-port protection before DNAT and user-space proxies.

The fence covers explicitly owned wildcard TCP publications. It does not claim
to isolate an entire Docker network or replace proof of application ownership.
Failure never removes installed protection; only successful recovery releases it.
"""
import ipaddress
from pathlib import Path
import re
import shlex
import stat

from recovery_engine import absolute, check_pin, digest, load, require, utc, write


def validate(configuration):
    require(type(configuration) is dict and set(configuration) ==
            {'schemaVersion', 'ports', 'allowedWriterIPv4', 'programs'} and
            configuration['schemaVersion'] == 'PublishedHostWriteFence/v1', 'PUBLISHED_FENCE_CONFIGURATION_INVALID')
    ports, writers = configuration['ports'], configuration['allowedWriterIPv4']
    require(type(ports) is list and 0 < len(ports) <= 15 and
            all(type(port) is int and 0 < port <= 65535 for port in ports) and
            ports == sorted(set(ports)), 'PUBLISHED_FENCE_PORTS_INVALID')
    require(type(writers) is list and len(writers) <= 32 and len(set(writers)) == len(writers),
            'PUBLISHED_FENCE_WRITERS_INVALID')
    for writer in writers:
        require(type(writer) is str, 'PUBLISHED_FENCE_WRITERS_INVALID')
        try: address = ipaddress.IPv4Address(writer)
        except ipaddress.AddressValueError as error: raise ValueError('PUBLISHED_FENCE_WRITERS_INVALID') from error
        require(str(address) == writer and not address.is_loopback and not address.is_unspecified and
                not address.is_multicast, 'PUBLISHED_FENCE_WRITERS_INVALID')
    programs = configuration['programs']
    require(type(programs) is dict and set(programs) == {'ipv4', 'ipv6'}, 'PUBLISHED_FENCE_PROGRAMS_INVALID')
    for family, applet in (('ipv4', 'iptables'), ('ipv6', 'ip6tables')):
        program = programs[family]
        require(type(program) is dict and set(program) == {'pin', 'applet'} and program['applet'] == applet and
                type(program['pin']) is dict and set(program['pin']) == {'path', 'bytes', 'sha256'} and
                Path(program['pin']['path']).name in ('xtables-multi', 'xtables-nft-multi', 'xtables-legacy-multi'),
                'PUBLISHED_FENCE_PROGRAMS_INVALID')
    return configuration


def _table(raw):
    result = {}
    try:
        for line in raw.decode('utf-8').splitlines():
            tokens = shlex.split(line)
            if not tokens: continue
            if tokens[0] in ('-P', '-N'):
                require(len(tokens) == (3 if tokens[0] == '-P' else 2) and tokens[1] not in result,
                        'PUBLISHED_FENCE_RULE_FORMAT_INVALID')
                result[tokens[1]] = dict(declaration=tokens, rules=[])
            else:
                require(len(tokens) > 2 and tokens[0] == '-A' and tokens[1] in result,
                        'PUBLISHED_FENCE_RULE_FORMAT_INVALID')
                result[tokens[1]]['rules'].append(tokens)
    except (UnicodeError, ValueError) as error:
        raise ValueError('PUBLISHED_FENCE_RULE_FORMAT_INVALID') from error
    require({'PREROUTING', 'OUTPUT'} <= set(result), 'PUBLISHED_FENCE_RULE_FORMAT_INVALID')
    return result


class PublishedFence:
    def __init__(self, configuration, operation_id, journal, execute):
        self.configuration = validate(configuration)
        require(type(operation_id) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,127}', operation_id),
                'PUBLISHED_FENCE_OPERATION_INVALID')
        self.operation_id, self.journal, self.execute = operation_id, absolute(str(journal)), execute
        prefix = 'SF_' + digest(operation_id)[:20]
        self.chains = {family: {hook: prefix+'_'+suffix+letter for hook, letter in
            (('PREROUTING', 'P'), ('OUTPUT', 'O'))} for family, suffix in (('ipv4', '4'), ('ipv6', '6'))}

    def _run(self, family, arguments, *, mutation=False):
        program = self.configuration['programs'][family]
        check_pin(program['pin'])
        require(stat.S_IMODE(absolute(program['pin']['path']).stat().st_mode) & 0o111,
                'PUBLISHED_FENCE_PROGRAM_NOT_EXECUTABLE')
        return self.execute([program['pin']['path'], program['applet'], '-w', '5', '-t', 'mangle',
                             *arguments], mutation=mutation)

    def _hook(self, family, hook):
        return [hook, '-m', 'addrtype', '--dst-type', 'LOCAL', '-p', 'tcp', '-m', 'multiport',
                '--dports', ','.join(map(str, self.configuration['ports'])), '-j', self.chains[family][hook]]

    def _rules(self, family, hook):
        if hook == 'PREROUTING':
            # Local packets also enter PREROUTING after loopback transmission.
            # OUTPUT has already enforced their root owner and loopback target.
            rules = [['-i', 'lo', '-s', '127.0.0.1/32' if family == 'ipv4' else '::1/128', '-j', 'RETURN']]
            if family == 'ipv4':
                rules += [['-s', address+'/32', '-j', 'RETURN'] for address in
                          self.configuration['allowedWriterIPv4']]
        else:
            rules = [['-d', '127.0.0.1/32' if family == 'ipv4' else '::1/128', '-m', 'owner',
                      '--uid-owner', '0', '-j', 'RETURN']]
        return [*rules, ['-j', 'DROP']]

    def install(self):
        before = self.preflight()
        self.journal.mkdir(mode=0o700)
        write(self.journal/'intent.json', dict(schemaVersion='PublishedHostWriteFenceIntent/v1',
            operationId=self.operation_id, configurationDigest=digest(self.configuration),
            originalTables=before, startedAt=utc()))
        expected = {}
        for family, chains in self.chains.items():
            for hook, chain in chains.items():
                self._run(family, ['-N', chain], mutation=True)
                for rule in self._rules(family, hook):
                    self._run(family, ['-A', chain, *rule], mutation=True)
                body = self._run(family, ['-S', chain]).decode('utf-8').splitlines()
                body = [shlex.split(line) for line in body if line.startswith('-A ')]
                require(len(body) == len(self._rules(family, hook)) and body[-1] == ['-A', chain, '-j', 'DROP'],
                        'PUBLISHED_FENCE_RULES_CHANGED')
                for rule in self._rules(family, hook): self._run(family, ['-C', chain, *rule])
            for hook in chains:
                rule = self._hook(family, hook)
                self._run(family, ['-I', hook, '1', *rule[1:]], mutation=True)
                self._run(family, ['-C', *rule])
            current = _table(self._run(family, ['-S']))
            require(set(current) == set(before[family]) | set(chains.values()), 'PUBLISHED_FENCE_RULES_CHANGED')
            for chain, original in before[family].items():
                observed = current[chain]
                require(observed['declaration'] == original['declaration'], 'PUBLISHED_FENCE_RULES_CHANGED')
                rules = observed['rules']
                if chain in chains:
                    require(rules and rules[0][-2:] == ['-j', chains[chain]], 'PUBLISHED_FENCE_RULES_CHANGED')
                    rules = rules[1:]
                require(rules == original['rules'], 'PUBLISHED_FENCE_RULES_CHANGED')
            expected[family] = current
            write(self.journal/(family+'-installed.json'), dict(state='INSTALLED', table=current, observedAt=utc()))
        write(self.journal/'active.json', dict(schemaVersion='PublishedHostWriteFenceActive/v1',
            operationId=self.operation_id, configurationDigest=digest(self.configuration), expectedTables=expected))
        self.verify()

    def preflight(self):
        require(not self.journal.exists(), 'PUBLISHED_FENCE_ALREADY_CLAIMED')
        before = {family: _table(self._run(family, ['-S'])) for family in self.chains}
        require(all(not set(chains.values()) & set(before[family]) for family, chains in self.chains.items()),
                'PUBLISHED_FENCE_CHAIN_ALREADY_EXISTS')
        return before

    def verify(self):
        active = load(self.journal/'active.json')
        require(active['schemaVersion'] == 'PublishedHostWriteFenceActive/v1' and
                active['operationId'] == self.operation_id and active['configurationDigest'] == digest(self.configuration) and
                not (self.journal/'released.json').exists(), 'PUBLISHED_FENCE_IDENTITY_CHANGED')
        require({family: _table(self._run(family, ['-S'])) for family in self.chains} == active['expectedTables'],
                'PUBLISHED_FENCE_RULES_CHANGED')

    def release(self):
        self.verify()
        intent = load(self.journal/'intent.json')
        require(intent['operationId'] == self.operation_id and
                intent['configurationDigest'] == digest(self.configuration), 'PUBLISHED_FENCE_IDENTITY_CHANGED')
        for family, chains in self.chains.items():
            for hook in chains: self._run(family, ['-D', *self._hook(family, hook)], mutation=True)
            for hook, chain in chains.items():
                for rule in reversed(self._rules(family, hook)):
                    self._run(family, ['-D', chain, *rule], mutation=True)
                self._run(family, ['-X', chain], mutation=True)
        require({family: _table(self._run(family, ['-S'])) for family in self.chains} == intent['originalTables'],
                'PUBLISHED_FENCE_ORIGINAL_RULES_CHANGED')
        return write(self.journal/'released.json', dict(schemaVersion='PublishedHostWriteFenceRelease/v1',
            operationId=self.operation_id, originalRulesPreserved=True, finishedAt=utc()))
