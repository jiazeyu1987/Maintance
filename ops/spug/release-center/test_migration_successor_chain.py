import unittest
from unittest.mock import patch
import intruoyi_runtime_agent as agent
from ops.release.release_preflight_plan import build_preflight_plan


class SuccessorChainTest(unittest.TestCase):
    def check(self, migrations, entries, applied=()):
        manifest = dict(migrations=migrations, publishScope='app-release', executionPlans={
            'test': dict(status='passed', targetEnvironment='test', items=entries)})
        audit = dict(applied=list(applied), missing=[m['migrationId'] for m in migrations if m['migrationId'] not in applied])
        with patch.object(agent, 'audit_ledger', return_value=audit):
            return agent.migration_plan(dict(environment='test'), manifest, {})

    def migration(self, name, replaces=(), depends=()):
        return dict(migrationId=name, type='schema', allowedEnvironments=['test'],
                    supersedes=list(replaces), dependsOn=list(depends))

    def test_transitive_skip_has_executable_terminal(self):
        migrations = [self.migration('A'), self.migration('B', ['A']), self.migration('C', ['B'])]
        entries = [dict(migrationId=n, action='SKIP_IMMUTABLE' if n != 'C' else 'APPLY') for n in ('A','B','C')]
        self.assertEqual(self.check(migrations, entries), entries)

    def test_dependency_resolves_to_completed_terminal(self):
        migrations = [self.migration('A'), self.migration('B',['A']), self.migration('C',['B']), self.migration('D',depends=['A'])]
        entries = [dict(migrationId=n,action='SKIP_IMMUTABLE' if n in ('A','B') else 'APPLY') for n in ('A','B','C','D')]
        self.assertEqual(self.check(migrations, entries), entries)

    def test_cycle_is_rejected(self):
        with self.assertRaisesRegex(agent.RuntimeBlocked, 'Cyclic'):
            self.check([self.migration('A',['B']),self.migration('B',['A'])],
                       [dict(migrationId=n,action='SKIP_IMMUTABLE') for n in ('A','B')])

    def test_ambiguous_successor_is_rejected(self):
        with self.assertRaisesRegex(agent.RuntimeBlocked, 'Ambiguous'):
            self.check([self.migration('A'),self.migration('B',['A']),self.migration('C',['A'])],
                       [dict(migrationId=n,action='APPLY') for n in ('A','B','C')])

    def test_excluded_terminal_cannot_justify_skip(self):
        with self.assertRaisesRegex(agent.RuntimeBlocked, 'Unexplained'):
            self.check([self.migration('A'),self.migration('B',['A'])],
                       [dict(migrationId='A',action='SKIP_IMMUTABLE'),dict(migrationId='B',action='SKIP_SCOPE_EXCLUDED')])

    def test_dependency_terminal_must_precede_dependent(self):
        with self.assertRaisesRegex(agent.RuntimeBlocked, 'dependency not applied'):
            self.check([self.migration('A'),self.migration('B',['A']),self.migration('C',depends=['A'])],
                       [dict(migrationId='A',action='SKIP_IMMUTABLE'),dict(migrationId='C',action='APPLY'),dict(migrationId='B',action='APPLY')])

    def test_applied_terminal_is_valid_proof(self):
        entries=[dict(migrationId='A',action='SKIP_IMMUTABLE'),dict(migrationId='B',action='SKIP_ALREADY_APPLIED')]
        self.assertEqual(self.check([self.migration('A'),self.migration('B',['A'])],entries,['B']),entries)

    def test_self_dependency_through_replacement_is_rejected(self):
        with self.assertRaisesRegex(agent.RuntimeBlocked, 'dependency not applied'):
            self.check([self.migration('A'),self.migration('B',['A'],['A'])],
                       [dict(migrationId='A',action='SKIP_IMMUTABLE'),dict(migrationId='B',action='APPLY')])

    def test_superseded_sql_cannot_be_applied(self):
        with self.assertRaisesRegex(agent.RuntimeBlocked, 'Superseded migration cannot'):
            self.check([self.migration('A'),self.migration('B',['A'])],
                       [dict(migrationId='A',action='APPLY'),dict(migrationId='B',action='APPLY')])

    def test_unknown_predecessor_is_rejected(self):
        with self.assertRaisesRegex(agent.RuntimeBlocked, 'Unknown superseded'):
            self.check([self.migration('B',['A'])],[dict(migrationId='B',action='APPLY')])

    def test_planner_and_runtime_agree_on_terminal_dependency(self):
        migrations = [self.migration('A'), self.migration('B',['A']),
                      self.migration('D',depends=['A']), self.migration('C',['B'])]
        for item in migrations:
            item.update(sha256='a'*64, requiresTargetPreflight=True, targetPreflight={})
        plan = build_preflight_plan(migrations, {}, target_environment='test', publish_scope='app-release')
        self.assertEqual(plan['status'], 'passed')
        actions = {item['migrationId']: item['action'] for item in plan['items']}
        self.assertEqual(actions, {'A':'SKIP_IMMUTABLE','B':'SKIP_IMMUTABLE','C':'APPLY','D':'APPLY'})
        order = [item['migrationId'] for item in plan['items']]
        self.assertLess(order.index('C'), order.index('D'))
        self.assertEqual(self.check(migrations, plan['items']), plan['items'])


if __name__ == '__main__':
    unittest.main()
