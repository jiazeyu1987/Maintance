"""Finite native nft restriction; not host-writer or full maintenance proof.

Owns one inet table, never edits Docker or another application's tables.
Actions and uncertainty use the existing maintenance claim. Neither an install
timeout nor an interrupted completion may replay an action. Native freeze and
the separately approved scheduler/administrator controls remain required.
"""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess

import formal_snapshot_linux as snapshot


def _require(ok, suffix):
    snapshot.require(ok, 'FORMAL_INGRESS_' + suffix)


def _digest(value):
    return hashlib.sha256(snapshot._canonical_bytes(value)).hexdigest()


def _table(binding_sha):
    _require(type(binding_sha) is str and re.fullmatch('[0-9a-f]{64}',binding_sha), 'PLAN_INVALID')
    return 'ir_maint_' + binding_sha[:24]


def _address(value):
    _require(type(value) is str, 'PLAN_INVALID')
    try: address=ipaddress.ip_address(value)
    except ValueError: raise snapshot.FormalSnapshotError('FORMAL_INGRESS_PLAN_INVALID') from None
    _require(str(address)==value and not address.is_unspecified and not address.is_multicast
             and '%' not in value, 'PLAN_INVALID')
    return 'ip' if address.version==4 else 'ip6'


def _ports(value):
    _require(type(value) is list and 0<len(value)<=32 and
        all(type(p) is int and 1<=p<=65535 and p!=22 for p in value) and
        len(set(value))==len(value), 'PLAN_INVALID')
    return '{ '+', '.join(str(p) for p in sorted(value))+' }'


def render_policy(binding_sha, plan):
    table=_table(binding_sha)
    _require(type(plan) is dict and set(plan)=={'bootId','networkNamespace','hostAddresses','hostPorts','targets'},'PLAN_INVALID')
    _require(type(plan['bootId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',plan['bootId']) and
        type(plan['networkNamespace']) is str and re.fullmatch(r'net:\[[0-9]+\]',plan['networkNamespace']), 'PLAN_INVALID')
    addresses=plan['hostAddresses'];targets=plan['targets']
    _require(type(addresses) is list and 2<=len(addresses)<=32 and all(type(a) is str for a in addresses) and
        len(set(addresses))==len(addresses), 'PLAN_INVALID')
    _require({_address(a) for a in addresses}=={'ip','ip6'},'PLAN_INVALID')
    ports=_ports(plan['hostPorts'])
    _require(type(targets) is list and 0<len(targets)<=32,'PLAN_INVALID')
    seen=set()
    for target in targets:
        _require(type(target) is dict and set(target)=={'address','ports'},'PLAN_INVALID')
        _address(target['address']);_ports(target['ports'])
        _require(target['address'] not in seen,'PLAN_INVALID');seen.add(target['address'])
    lines=[f'create table inet {table}']
    for hook in ('input','forward','output'):
        lines.append(f'add chain inet {table} {hook} {{ type filter hook {hook} priority -10; }}')
    # INPUT covers every host address, including unplanned newly assigned ones.
    # No established-connection accept: existing business sessions are fenced too.
    lines.append(f'add rule inet {table} input tcp dport {ports} drop')
    for addr in sorted(addresses):
        lines.append(f'add rule inet {table} output {_address(addr)} daddr {addr} tcp dport {ports} drop')
    for target in sorted(targets,key=lambda item:item['address']):
        for hook in ('forward','output'):
            lines.append(f'add rule inet {table} {hook} {_address(target["address"])} daddr {target["address"]} tcp dport {_ports(target["ports"])} drop')
    return ('\n'.join(lines)+'\n').encode('ascii')


def render_recovery_policy(binding_sha, plan, flows):
    """Permit exact forwarded dependency traffic; host business ports stay closed.

    This does not authenticate the source workload. The caller must bind the
    approved addresses to exact recovery actors and maintain host exclusion.
    Neither this finite rule transition nor its receipt proves that boundary.
    """
    render_policy(binding_sha,plan)
    _require(type(flows) is list and 0<len(flows)<=32,'RECOVERY_PLAN_INVALID')
    targets={t['address']:set(t['ports']) for t in plan['targets']};seen=set()
    for flow in flows:
        _require(type(flow) is dict and set(flow)=={'source','destination','ports'},'RECOVERY_PLAN_INVALID')
        source=flow['source'];destination=flow['destination'];ports=flow['ports']
        try:
            family=_address(source);target_family=_address(destination);_ports(ports)
        except snapshot.FormalSnapshotError:
            raise snapshot.FormalSnapshotError('FORMAL_INGRESS_RECOVERY_PLAN_INVALID') from None
        _require(source!=destination and source not in plan['hostAddresses'] and
            not ipaddress.ip_address(source).is_loopback and family==target_family and
            destination in targets and set(ports)<=targets[destination],'RECOVERY_PLAN_INVALID')
        key=(source,destination,tuple(sorted(ports)))
        _require(key not in seen,'RECOVERY_PLAN_INVALID');seen.add(key)
    table=_table(binding_sha)
    # Each insert prepends. Reverse command order to preserve the approved order
    # in kernel readback, ahead of the existing FORWARD target drops.
    return ''.join(f'insert rule inet {table} forward {_address(f["source"])} saddr {f["source"]} '
        f'{_address(f["destination"])} daddr {f["destination"]} tcp dport {_ports(f["ports"])} return\n'
        for f in reversed(flows)).encode('ascii')


def render_recovery_transition(binding_sha,plan,flows,table_handle):
    _require(type(table_handle) is int and table_handle>0,'RECOVERY_PLAN_INVALID')
    # One atomic batch: a stale table handle aborts the whole transaction before
    # a same-name replacement can be touched. This is not a rules-digest CAS;
    # exclusive trusted host control is still a required caller boundary.
    return (f'delete table inet handle {table_handle}\n'.encode('ascii')+
            render_policy(binding_sha,plan)+render_recovery_policy(binding_sha,plan,flows))


def _verify_applied_policy(table, plan, observed):
    """Check kernel semantics against the requested scope before retaining handles."""
    def match(protocol,field,value):
        return {'match':{'op':'==','left':{'payload':{'protocol':protocol,'field':field}},'right':value}}
    def port_value(ports):
        return ports[0] if len(ports)==1 else {'set':sorted(ports)}
    def rule(chain,address,ports):
        expr=[] if address is None else [match(_address(address),'daddr',address)]
        expr += [match('tcp','dport',port_value(ports)),{'drop':None}]
        return {'rule':{'family':'inet','table':table,'chain':chain,'expr':expr}}
    expected=[{'table':{'family':'inet','name':table}}]
    for hook in ('input','forward','output'):
        expected.append({'chain':{'family':'inet','table':table,'name':hook,'type':'filter',
                                 'hook':hook,'prio':-10,'policy':'accept'}})
    rules={'input':[rule('input',None,plan['hostPorts'])], 'forward':[], 'output':[]}
    for address in sorted(plan['hostAddresses']):
        rules['output'].append(rule('output',address,plan['hostPorts']))
    for target in sorted(plan['targets'],key=lambda item:item['address']):
        for hook in ('forward','output'):
            rules[hook].append(rule(hook,target['address'],target['ports']))
    # nft lists table/chain declarations, then rules grouped by chain.
    expected += [entry for hook in ('input','forward','output') for entry in rules[hook]]
    normalized=[]
    _require(type(observed) is list,'APPLIED_POLICY_CHANGED')
    for entry in observed:
        _require(type(entry) is dict and len(entry)==1,'APPLIED_POLICY_CHANGED')
        kind,body=next(iter(entry.items()))
        _require(kind in ('table','chain','rule') and type(body) is dict and
            type(body.get('handle')) is int and body['handle']>0,'APPLIED_POLICY_CHANGED')
        normalized.append({kind:{key:value for key,value in body.items() if key!='handle'}})
    _require(normalized==expected,'APPLIED_POLICY_CHANGED')


class NativeNft:
    """The current bound Linux network namespace; no shell or alternate backend."""
    def identity(self):
        return {'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'networkNamespace':os.readlink('/proc/self/ns/net')}

    def run(self, arguments, raw=None):
        try:
            result=subprocess.run(['/usr/sbin/nft',*arguments],input=raw,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,
                timeout=snapshot.observation_timeout(15),
                env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL':'C'})
        except (OSError,subprocess.TimeoutExpired):
            raise snapshot.FormalSnapshotError('FORMAL_INGRESS_COMMAND_UNCERTAIN') from None
        _require(result.returncode==0 and not result.stderr and len(result.stdout)<=1024*1024,'COMMAND_FAILED')
        return result.stdout

    def inspect(self, table):
        # list tables distinguishes absence from denied access/tool failure.
        try: tables=json.loads(self.run(['-j','list','tables']))['nftables']
        except (ValueError,KeyError,TypeError):
            raise snapshot.FormalSnapshotError('FORMAL_INGRESS_READBACK_INVALID') from None
        if not any(x.get('table',{}).get('family')=='inet' and x.get('table',{}).get('name')==table for x in tables):
            return None
        try: value=json.loads(self.run(['-j','-a','list','table','inet',table]))['nftables']
        except (ValueError,KeyError,TypeError):
            raise snapshot.FormalSnapshotError('FORMAL_INGRESS_READBACK_INVALID') from None
        # Metadata is client version information, not kernel rule identity.
        return [x for x in value if 'metainfo' not in x]


def _event(claim, step):
    return next((x['details'] for x in claim.events if x['step']==step),None)


def _bound(claim, native):
    claim.assert_owned()
    scope=_event(claim,'ingress-scope')
    _require(scope is not None,'SCOPE_REQUIRED')
    path=claim.root/'ingress-plan.json';raw=claim._read(path)
    try: plan=json.loads(raw)
    except (ValueError,UnicodeError):
        raise snapshot.FormalSnapshotError('FORMAL_INGRESS_PLAN_CHANGED') from None
    _require(raw==snapshot._canonical_bytes(plan) and hashlib.sha256(raw).hexdigest()==scope['planSha256'],'PLAN_CHANGED')
    binding_sha=hashlib.sha256(claim._plan).hexdigest()
    policy=render_policy(binding_sha,plan)
    _require(hashlib.sha256(policy).hexdigest()==scope['policySha256'] and scope['table']==_table(binding_sha),'PLAN_CHANGED')
    _require(native.identity()=={k:plan[k] for k in ('bootId','networkNamespace')},'HOST_CHANGED')
    return scope,policy


def install_ingress(claim, plan, *, guard, native=None):
    _require(callable(guard),'MUTATION_GUARD_REQUIRED')
    # Freeze approval before the first external callback.
    plan=json.loads(snapshot._canonical_bytes(plan))
    def checked():
        snapshot.observation_timeout(1);claim.assert_owned();guard();claim.assert_owned();snapshot.observation_timeout(1)
    checked()
    native=NativeNft() if native is None else native
    claim.assert_owned()
    _require(_event(claim,'ingress-scope') is None,'ACTION_ALREADY_STARTED')
    binding_sha=hashlib.sha256(claim._plan).hexdigest();policy=render_policy(binding_sha,plan)
    _require(native.identity()=={k:plan[k] for k in ('bootId','networkNamespace')},'HOST_CHANGED')
    table=_table(binding_sha);_require(native.inspect(table) is None,'TABLE_EXISTS')
    native.run(['-c','-f','-'],policy)
    raw=snapshot._canonical_bytes(plan)
    claim._write(claim.root/'ingress-plan.json',raw)
    claim.record('ingress-scope',{'table':table,'planSha256':hashlib.sha256(raw).hexdigest(),
                               'policySha256':hashlib.sha256(policy).hexdigest()})
    _bound(claim,native)
    claim.record('ingress-install-intent',{})
    _bound(claim,native);checked()
    native.run(['-f','-'],policy)
    checked()
    _bound(claim,native)
    observed=native.inspect(table);_require(observed is not None,'TABLE_MISSING')
    _verify_applied_policy(table,plan,observed)
    checked()
    # Store kernel-assigned handles so a recreated table cannot pass a guard.
    claim._write(claim.root/'ingress-installed.json',snapshot._canonical_bytes(observed))
    claim.record('ingress-installed',{'rulesSha256':_digest(observed)})
    result=assert_ingress(claim,native=native);checked()
    return result


def assert_ingress(claim, *, native=None):
    native=NativeNft() if native is None else native
    scope,_=_bound(claim,native);installed=_event(claim,'ingress-installed')
    _require(installed is not None and _event(claim,'ingress-release-intent') is None,'NOT_HELD')
    raw=claim._read(claim.root/'ingress-installed.json');digest=installed['rulesSha256']
    _require(hashlib.sha256(raw).hexdigest()==digest,'RECORD_CHANGED')
    recovery=_event(claim,'ingress-recovery-intent')
    if recovery is not None:
        completed=_event(claim,'ingress-recovery-permitted')
        _require(completed is not None,'RECOVERY_UNCERTAIN_RETAINED')
        plan_raw=claim._read(claim.root/'ingress-recovery-plan.json')
        _require(hashlib.sha256(plan_raw).hexdigest()==recovery['planSha256'] and
            recovery['originalRulesSha256']==digest and
            recovery['tableHandle']==json.loads(raw)[0]['table']['handle'],'RECORD_CHANGED')
        flows=json.loads(plan_raw);plan=json.loads(claim._read(claim.root/'ingress-plan.json'))
        _require(plan_raw==snapshot._canonical_bytes(flows) and
            hashlib.sha256(render_recovery_transition(hashlib.sha256(claim._plan).hexdigest(),plan,
                flows,recovery['tableHandle'])).hexdigest()==recovery['policySha256'],'RECORD_CHANGED')
        digest=completed['rulesSha256'];raw=claim._read(claim.root/'ingress-recovery-installed.json')
        _require(hashlib.sha256(raw).hexdigest()==digest and completed['planSha256']==recovery['planSha256'],
                 'RECORD_CHANGED')
    actual=native.inspect(scope['table'])
    _require(actual is not None and snapshot._canonical_bytes(actual)==raw,'RULES_CHANGED')
    claim.assert_owned()
    return {'state':'INGRESS_HELD_PENDING_HOST_AND_TRAFFIC_PROOF','table':scope['table'],
            'tableHandle':actual[0]['table']['handle'],
            'rulesSha256':digest,'fullWriterExclusion':False,
            'phase':'RECOVERY_DEPENDENCIES_PERMITTED' if recovery else 'CAPTURE_RESTRICTED'}


def permit_recovery_dependencies(claim, flows, *, guard, thaw_guard, native=None):
    """One explicit retained transition, after thaw; never replay uncertainty.

    Approval/actor bindings and full host controls belong to the standard
    runner's guard. This primitive only changes and verifies its own nft table.
    Raw/SQL capture is permanently refused after the transition intent.
    """
    _require(callable(guard) and callable(thaw_guard),'RECOVERY_GUARD_REQUIRED')
    # Snapshot inputs before a callback may mutate the caller's objects.
    try:
        raw=snapshot._canonical_bytes(flows);flows=json.loads(raw)
    except (ValueError,TypeError,UnicodeError):
        raise snapshot.FormalSnapshotError('FORMAL_INGRESS_RECOVERY_PLAN_INVALID') from None
    _require(len(raw)<=16384,'RECOVERY_PLAN_INVALID')
    thaw_guard();claim.assert_owned()
    native=NativeNft() if native is None else native
    _require(_event(claim,'ingress-recovery-intent') is None,'RECOVERY_ALREADY_STARTED')
    held=assert_ingress(claim,native=native);guard();thaw_guard()
    _bound(claim,native)
    plan=json.loads(claim._read(claim.root/'ingress-plan.json'))
    policy=render_recovery_transition(hashlib.sha256(claim._plan).hexdigest(),plan,flows,held['tableHandle'])
    native.run(['-c','-f','-'],policy)
    original=json.loads(claim._read(claim.root/'ingress-installed.json'))
    claim._write(claim.root/'ingress-recovery-plan.json',raw)
    guard();thaw_guard();assert_ingress(claim,native=native)
    claim.record('ingress-recovery-intent',{'planSha256':hashlib.sha256(raw).hexdigest(),
        'originalRulesSha256':held['rulesSha256'],'tableHandle':held['tableHandle'],
        'policySha256':hashlib.sha256(policy).hexdigest()})
    native.run(['-f','-'],policy)
    thaw_guard();_bound(claim,native)
    observed=native.inspect(held['table'])
    _verify_recovery_rules(original,observed,held['table'],flows,plan)
    _require(claim._read(claim.root/'ingress-recovery-plan.json')==raw,'RECORD_CHANGED')
    claim._write(claim.root/'ingress-recovery-installed.json',snapshot._canonical_bytes(observed))
    claim.record('ingress-recovery-permitted',{'planSha256':hashlib.sha256(raw).hexdigest(),
                                            'rulesSha256':_digest(observed)})
    result=assert_ingress(claim,native=native);guard();thaw_guard()
    return result


def _verify_recovery_rules(original,observed,table,flows,plan):
    _require(type(observed) is list,'RECOVERY_POLICY_CHANGED')
    def rule(flow):
        family=_address(flow['source']);ports=flow['ports']
        matches=[{'match':{'op':'==','left':{'payload':{'protocol':family,'field':field}},'right':value}}
            for field,value in [('saddr',flow['source']),('daddr',flow['destination'])]]
        matches += [{'match':{'op':'==','left':{'payload':{'protocol':'tcp','field':'dport'}},
                             'right':ports[0] if len(ports)==1 else {'set':sorted(ports)}}},{'return':None}]
        return {'rule':{'family':'inet','table':table,'chain':'forward','expr':matches}}
    def semantics(entries):
        return [{kind:{k:v for k,v in body.items() if k!='handle'}}
            for entry in entries for kind,body in entry.items()]
    _require(observed and observed[0].get('table',{}).get('handle')!=original[0]['table']['handle'],
             'RECOVERY_POLICY_CHANGED')
    originals=[entry for entry in original if entry.get('rule',{}).get('chain')!='forward']
    retained=[entry for entry in observed if entry.get('rule',{}).get('chain')!='forward']
    _require(semantics(retained)==semantics(originals),'RECOVERY_POLICY_CHANGED')
    original_forward=[entry for entry in original if entry.get('rule',{}).get('chain')=='forward']
    current=[entry for entry in observed if entry.get('rule',{}).get('chain')=='forward']
    _require(len(current)==len(flows)+len(original_forward) and
        semantics(current[len(flows):])==semantics(original_forward),
             'RECOVERY_POLICY_CHANGED')
    base=[entry for entry in observed if entry not in current[:len(flows)]]
    _verify_applied_policy(table,plan,base)
    handles=[]
    for entry in observed[1:]:
        handle=next(iter(entry.values())).get('handle')
        _require(type(handle) is int and handle>0 and handle not in handles,'RECOVERY_POLICY_CHANGED')
        handles.append(handle)
    for entry,flow in zip(current,flows):
        body=entry.get('rule',{});handle=body.get('handle')
        _require({'rule':{k:v for k,v in body.items() if k!='handle'}}==rule(flow),'RECOVERY_POLICY_CHANGED')


def release_ingress(claim, health_guard, *, native=None):
    native=NativeNft() if native is None else native
    _require(callable(health_guard),'HEALTH_GUARD_REQUIRED')
    assert_ingress(claim,native=native)
    health_guard()
    held=assert_ingress(claim,native=native)
    claim.record('ingress-release-intent',{'rulesSha256':held['rulesSha256'],'tableHandle':held['tableHandle']})
    # The kernel handle prevents deleting an unrelated table recreated with the
    # same name between our last observation and this atomic transaction.
    native.run(['-f','-'],f'delete table inet handle {held["tableHandle"]}\n'.encode('ascii'))
    _bound(claim,native)
    _require(native.inspect(held['table']) is None,'RELEASE_UNCERTAIN')
    claim.record('ingress-released',{'table':held['table']})
    return {'state':'INGRESS_RELEASED','table':held['table']}


def observe_ingress_reconciliation(claim, *, native=None):
    """Read-only classification. Uncertain apply never becomes a held receipt."""
    native=NativeNft() if native is None else native
    scope,_=_bound(claim,native);actual=native.inspect(scope['table'])
    result={'table':scope['table'],'present':actual is not None,'actionReplayed':False}
    if _event(claim,'ingress-released') is not None:
        _require(actual is None,'RULES_CHANGED');result['state']='RELEASED'
    elif _event(claim,'ingress-release-intent') is not None:
        result['state']='RELEASE_UNCERTAIN_RETAINED'
    elif _event(claim,'ingress-recovery-intent') is not None and _event(claim,'ingress-recovery-permitted') is None:
        result['state']='RECOVERY_UNCERTAIN_RETAINED'
    elif _event(claim,'ingress-installed') is not None:
        assert_ingress(claim,native=native);result['state']='HELD'
    else: result['state']='INSTALL_UNCERTAIN_RETAINED'
    return result
