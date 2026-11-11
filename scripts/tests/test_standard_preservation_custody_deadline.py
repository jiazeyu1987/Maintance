"""Reject premature deadline transfers on a real prepared packaged owner."""
import importlib

import pytest

from test_recovery_target_preservation import publication_case
from test_recovery_target_capture_session import (
    case, restore_case, capture_protocol, claim, locked, started, context, construct)


def test_prepared_publication_cannot_transfer_deadline_without_verified_final(publication_case):
    h = publication_case
    claim(h.case)
    module = importlib.import_module('recovery_target_preservation')
    from repository_records import RepositoryError
    from recovery_engine import Budget

    with locked(h.case) as fd:
        _, binding, _ = started(h, fd)
        with context(h, binding, fd, budget=Budget(240000)) as ctx:
            native = construct(h, ctx)
            publication = module.TargetPreservation.prepare(native,
                policy_pin=h.preservation_policy, reservation_pin=h.reservation)
            assert publication._restoration_custody is None
            original_end = publication.deadline.end
            original_state = publication.session._state
            before = list(h.engine.actions)
            try:
                publication.deadline.end = 0
                with pytest.raises(RepositoryError, match='^PRESERVATION_DEADLINE$'):
                    publication._check_resources()
                publication.session._state = 'HANDED_OFF'
                with pytest.raises(RepositoryError, match='^PRESERVATION_DEADLINE$'):
                    publication._check_resources()
                publication._restoration_custody = object()
                with pytest.raises(RepositoryError, match='^PRESERVATION_CUSTODY_CHANGED$'):
                    publication._check_resources()
                assert h.engine.actions == before
                assert not (publication.root / 'preservation.json').exists()
            finally:
                publication._restoration_custody = None
                publication.session._state = original_state
                publication.deadline.end = original_end
                publication.close()
