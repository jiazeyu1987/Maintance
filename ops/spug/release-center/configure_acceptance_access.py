"""Explicit one-time firewalld setup; never run automatically by a release job."""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import shlex
import subprocess
from urllib.parse import urlsplit
from intruoyi_runtime import Runtime


REMOTE = r'''
import json,os,subprocess,sys
v=json.loads(sys.argv[1])
assert os.environ['SSH_CONNECTION'].split()[0]==v['source'], 'Executor source differs from approved address'
rule='rule family="ipv4" source address="'+v['source']+'/32" port port="'+str(v['port'])+'" protocol="tcp" accept'
def invoke(args):
 x=subprocess.run(['firewall-cmd','--zone='+v['zone']]+args,capture_output=True,text=True)
 return x
result={'zone':v['zone'],'source':v['source'],'port':v['port'],'changed':[]}
for persistent in (True,False):
 args=['--permanent'] if persistent else []
 q=invoke(args+['--query-rich-rule='+rule])
 assert q.returncode in (0,1), 'Firewall query failed'
 if q.returncode==1:
  assert invoke(args+['--add-rich-rule='+rule]).returncode==0, 'Firewall rule setup failed'
  result['changed'].append('permanent' if persistent else 'runtime')
 assert invoke(args+['--query-rich-rule='+rule]).returncode==0, 'Firewall rule verification failed'
print(json.dumps(result))
'''


def configure(config, env, source, zone):
    source = str(ipaddress.IPv4Address(source))
    if not re.fullmatch('[a-zA-Z0-9_-]+', zone):
        raise ValueError('Explicit firewalld zone required')
    runtime = Runtime(config)
    profile = runtime.profile(env)
    url = urlsplit(profile['acceptanceUrl'])
    if url.scheme != 'http' or url.hostname != profile['host'] or not url.port:
        raise ValueError('Explicit registered acceptance host and port required')
    value = json.dumps(dict(source=source,port=url.port,zone=zone))
    command = shlex.quote(profile['python'])+' -c '+shlex.quote(REMOTE)+' '+shlex.quote(value)
    result = subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],command],
                            capture_output=True,timeout=30)
    if result.returncode:
        raise RuntimeError('Acceptance access setup failed; inspect the registered zone/source and partial rule state')
    return json.loads(result.stdout)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--environment',choices=('test','prod','backup'),required=True)
    parser.add_argument('--source-ip',required=True)
    parser.add_argument('--zone',required=True)
    parser.add_argument('--apply',action='store_true',required=True)
    args=parser.parse_args()
    print(json.dumps(configure(json.loads(Path(args.config).read_text('utf-8-sig')),
                               args.environment,args.source_ip,args.zone)))
