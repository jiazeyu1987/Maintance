"""Authenticated SAFE fresh-process constructor boundary, actual Linux locks.

The existing formal constructor fixture uses actual private metadata, immutable
reservations, epoch journal, flock, ctx and MinimalData.__init__. It raises at
the first external database method, never synthesizes a successful database.
This pure candidate suite does not replace the post-commit real dual packages.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_target_preservation_packaged_capture import builder, safe_payload, safe_candidate_directory

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='real Linux constructor/flock contract, not a Windows emulation')


@pytest.mark.parametrize('phase', ['preparation', 'restore'])
def test_safe_candidate_actual_constructor_binds_before_first_database(safe_candidate_directory, tmp_path, phase):
    script = r'''
from pathlib import Path
import hashlib,sys
engine,tests,work=map(Path,sys.argv[1:4]);phase=sys.argv[4]
sys.path[:0]=[str(engine/'common'),str(engine/'formal'),str(tests)]
import recovery_minimal_runtime as runtime
import recovery_program_native as native
import recovery_target_capture as capture
import recovery_target_preservation as preservation
import recovery_capture_materials as materials
import minimal_capture_support as support
import formal_capture_semantics as semantics
assert runtime.supports_main_target_preservation is True
assert support.MinimalSemantic.__mro__[1] is semantics.SemanticCapture
for module,folder in ((runtime,'common'),(native,'common'),(capture,'common'),
        (preservation,'common'),(materials,'common'),(support,'formal'),(semantics,'formal')):
 path=Path(module.__file__).resolve()
 assert path.parent==(engine/folder).resolve()
 print('ACTUAL_CANDIDATE_MODULE '+str(path)+' SHA256='+hashlib.sha256(path.read_bytes()).hexdigest(),flush=True)
from test_recovery_program_native_constructor import exercise_constructor
exercise_constructor(work,engine/'formal','standard',phase)
print('ACTUAL_SAFE_CONSTRUCTOR_FIRST_DATABASE_PASS '+phase,flush=True)
'''
    result = subprocess.run([sys.executable,'-B','-c',script,str(safe_candidate_directory),
        str(ROOT/'scripts/tests'),str(tmp_path),phase],capture_output=True,timeout=180,
        env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)})
    print(result.stdout.decode('utf-8', errors='replace'),flush=True)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.rstrip().endswith(('ACTUAL_SAFE_CONSTRUCTOR_FIRST_DATABASE_PASS '+phase).encode())
