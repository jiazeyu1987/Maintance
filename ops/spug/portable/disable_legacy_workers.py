"""Imported release-center copies must not replay the original Spug task queues."""
from pathlib import Path
import re


def disable(text):
    for name in ('spug-worker','spug-monitor','spug-scheduler'):
        pattern=r'(?ms)(^\[program:'+re.escape(name)+r'\]\n)(.*?)(?=^\[|\Z)'
        matches=list(re.finditer(pattern,text))
        if len(matches)!=1:
            raise RuntimeError('Expected one supervisor section: '+name)
        match=matches[0]
        body,count=re.subn(r'(?m)^autostart[ \t]*=[ \t]*(true|false)[ \t]*$', 'autostart = false',match.group(2))
        if count!=1:
            raise RuntimeError('Expected one autostart setting: '+name)
        text=text[:match.start()]+match.group(1)+body+text[match.end():]
    return text


if __name__=='__main__':
    file=Path('/etc/supervisord.conf')
    file.write_text(disable(file.read_text(encoding='utf-8')),encoding='utf-8')
