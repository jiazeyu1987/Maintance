"""Reuse the established genuine read-only user path for either destination."""
from common import TASK
source=(TASK.parent/'20261105-spug-full-to-prod/verify_business_ui.cjs').read_text(encoding='utf-8')
source=source.replace("const label=process.argv[2]||'production-before-restore';", "const suffix=process.argv[2],phase=process.argv[3];if(!['57','58','59'].includes(suffix)||!['before','after'].includes(phase))throw Error('TARGET_AND_PHASE_REQUIRED');const label=suffix+'-'+phase;const base='http://172.30.30.'+suffix+':'+(suffix==='59'?'38081':'8081');")
source=source.replace("'http://172.30.30.57:8081/login?redirect=/index'", "base+'/login?redirect=/index'")
source=source.replace('C:/Spug/runtime/private/full-to-prod-20261105','C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
assert "base+'/login" in source and 'const suffix=' in source
destination=TASK/'verify_business_ui.cjs';assert not destination.exists()
destination.write_text(source,encoding='utf-8');assert destination.read_text(encoding='utf-8')==source
