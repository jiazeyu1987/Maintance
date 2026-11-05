"""Real IPv4 DNAT, IPv6 proxy, local UID and existing-rule preservation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_engine import pin


def command(args,**kwargs):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=10)
    return result.stdout


def probe(address,port,namespace=None,source=None,uid=None):
    program='import socket,sys;s=socket.socket(socket.AF_INET6 if ":" in sys.argv[1] else socket.AF_INET);s.settimeout(.6);'
    if source:program+='s.bind(('+repr(source)+',0));'
    program+='s.connect((sys.argv[1],int(sys.argv[2])));s.sendall(b"GET / HTTP/1.0\\r\\n\\r\\n");assert b"200" in s.recv(64)'
    args=[sys.executable,'-c',program,address,str(port)]
    if namespace:args=['ip','netns','exec',namespace,*args]
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12,
        preexec_fn=(lambda:os.setuid(uid)) if uid is not None else None)
    return result.returncode==0


def serve(port,host,namespace=None):
    code=('import socket\n'
          's=socket.socket(socket.AF_INET6 if ":" in '+repr(host)+' else socket.AF_INET)\n'
          's.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)\n'
          's.bind(('+repr(host)+','+str(port)+'))\n'
          's.listen(16)\n'
          'while True:\n'
          ' c,a=s.accept()\n'
          ' with c:\n'
          '  c.recv(4096)\n'
          '  c.sendall(b"HTTP/1.0 200 OK\\r\\nContent-Length: 2\\r\\n\\r\\nOK")\n')
    args=[sys.executable,'-u','-c',code]
    if namespace:args=['ip','netns','exec',namespace,*args]
    return subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def test_real_published_write_fence_blocks_dnat_and_proxy_without_changing_other_rules(tmp_path):
    from recovery_published_fence import PublishedFence
    namespaces=['fence-client','fence-data'];processes=[];nat=[];preexisting=[]
    try:
        for name in namespaces:
            command(['ip','netns','add',name]);command(['ip','-n',name,'link','set','lo','up'])
        for prefix,namespace,subnet in [('fc','fence-client','198.18.0'),('fd','fence-data','198.19.0')]:
            command(['ip','link','add',prefix+'host','type','veth','peer','name',prefix+'peer'])
            command(['ip','link','set',prefix+'peer','netns',namespace])
            command(['ip','addr','add',subnet+'.1/24','dev',prefix+'host'])
            command(['ip','link','set',prefix+'host','up'])
            command(['ip','-n',namespace,'addr','add',subnet+'.2/24','dev',prefix+'peer'])
            command(['ip','-n',namespace,'link','set',prefix+'peer','up'])
            command(['ip','-n',namespace,'route','add','default','via',subnet+'.1'])
        command(['ip','-n','fence-client','addr','add','198.18.0.3/24','dev','fcpeer'])
        command(['ip','addr','add','fd00:18::1/64','dev','fchost'])
        command(['ip','-n','fence-client','addr','add','fd00:18::2/64','dev','fcpeer'])
        assert Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()=='1'
        nat=[['PREROUTING','-p','tcp','-d','198.18.0.1','--dport','9000','-j','DNAT','--to-destination','198.19.0.2:9000'],
             ['OUTPUT','-p','tcp','-d','198.18.0.1','--dport','9000','-j','DNAT','--to-destination','198.19.0.2:9000'],
             ['POSTROUTING','-p','tcp','-d','198.19.0.2','--dport','9000','-j','MASQUERADE']]
        for rule in nat:command(['iptables','-t','nat','-A',*rule])
        for tool in ('iptables','ip6tables'):
            for chain in ('PREROUTING','OUTPUT'):
                rule=[tool,'-t','mangle','-A',chain,'-j','ACCEPT'];command(rule);preexisting.append(rule)
        processes=[serve(9000,'0.0.0.0','fence-data'),serve(9000,'127.0.0.1'),serve(9001,'::'),serve(9002,'0.0.0.0')]
        for _ in range(30):
            if probe('198.18.0.1',9000,'fence-client') and probe('fd00:18::1',9001,'fence-client'):break
            time.sleep(.1)
        assert probe('198.18.0.1',9000,'fence-client')
        assert probe('127.0.0.1',9000)
        assert probe('198.18.0.1',9000,uid=65534)
        assert probe('fd00:18::1',9001,'fence-client')
        before={tool:command([tool,'-t','mangle','-S']) for tool in ('iptables','ip6tables')}
        programs={family:dict(pin=pin(str(Path('/usr/sbin/'+tool).resolve())),applet=tool)
            for family,tool in [('ipv4','iptables'),('ipv6','ip6tables')]}
        configuration=dict(schemaVersion='PublishedHostWriteFence/v1',ports=[9000,9001],
            allowedWriterIPv4=['198.18.0.3'],programs=programs)
        fence=PublishedFence(configuration,'real-network-observation',tmp_path/'fence',command)
        fence.install();fence.verify()
        assert not probe('198.18.0.1',9000,'fence-client',source='198.18.0.2')
        assert probe('198.18.0.1',9000,'fence-client',source='198.18.0.3')
        assert probe('127.0.0.1',9000)
        assert not probe('127.0.0.1',9000,uid=65534)
        assert not probe('198.18.0.1',9000,uid=65534)
        assert not probe('fd00:18::1',9001,'fence-client')
        assert probe('198.18.0.1',9002,'fence-client')
        # An ACCEPT prepended by another actor invalidates effective order.
        command(['iptables','-t','mangle','-I','PREROUTING','1','-j','ACCEPT'])
        with pytest.raises(Exception,match='PUBLISHED_FENCE_RULES_CHANGED'):fence.verify()
        command(['iptables','-t','mangle','-D','PREROUTING','1'])
        fence.verify()
        # The failure did not automatically release the fence.
        assert not probe('198.18.0.1',9000,'fence-client',source='198.18.0.2')
        fence.release()
        assert probe('198.18.0.1',9000,'fence-client',source='198.18.0.2')
        assert probe('fd00:18::1',9001,'fence-client')
        assert {tool:command([tool,'-t','mangle','-S']) for tool in before}==before
    finally:
        for process in processes:
            process.terminate();process.wait(timeout=5)
        for rule in reversed(preexisting):
            args=list(rule);args[3]='-D';command(args)
        for rule in reversed(nat):command(['iptables','-t','nat','-D',*rule])
        for name in reversed(namespaces):
            subprocess.run(['ip','netns','delete',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for name in ('fchost','fdhost'):
            subprocess.run(['ip','link','delete',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
