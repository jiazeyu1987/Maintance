"""Actual STANDARD repository export contract; no injected missing symbols."""
import hashlib
import importlib
import json
import os
from pathlib import Path

import pytest


def test_actual_standard_material_entry_rejects_unowned_publication():
    assert os.name == 'posix', 'NATIVE_LINUX_CANDIDATE_REQUIRED'
    root = Path(os.environ['RECOVERY_TEST_FORMAL_DIRECTORY']).parent
    manifest = json.loads((root / 'package.json').read_bytes())
    assert manifest['variant'] == 'standard' and manifest['candidateOnly'] is True
    module = importlib.import_module('repository_minimal')
    path = root / 'common/repository_minimal.py'
    assert Path(module.__file__).resolve() == path.resolve()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['files'][
        'common/repository_minimal.py']
    # This is the same lazy export the real MAIN producer calls. A caller's
    # arbitrary materials/publication may never become a publication capability.
    entry = module.publish_materials
    from repository_records import RepositoryError
    with pytest.raises(RepositoryError, match='PRESERVATION_MATERIAL_OWNER_REQUIRED'):
        entry(object(), object(), publication=object(), deadline=object())
