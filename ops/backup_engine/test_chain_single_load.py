import ast
import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from build_variants import standard_sources
from standard_fixes import apply


class ChainLoadTests(unittest.TestCase):
    def fixture(self, directory):
        payload, _ = standard_sources()
        tree = ast.parse(apply(payload)['common/repository_minimal.py'])
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MinimumCatalog')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'chain')
        def read_pin(pin, **kwargs):
            raw = Path(pin['path']).read_bytes()
            if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
                raise ValueError('PIN_CHANGED')
            return raw
        def require(ok, message):
            if not ok: raise ValueError(message)
        namespace = dict(document=json.loads, read_pin=read_pin, require=require, timestamp=__import__('datetime').datetime.fromisoformat)
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<actual-standard-chain>', 'exec'), namespace)
        def write(name, value):
            raw = json.dumps(value).encode() if isinstance(value, dict) else value
            path = Path(directory)/name
            path.write_bytes(raw)
            return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        refs = []
        for i in range(3):
            content = write('payload'+str(i), ('payload'+str(i)).encode())
            refs.append(write('point'+str(i), dict(parentPointPins=list(refs), generationId='g',
                pointType='FULL' if i == 0 else 'INCREMENTAL', content=content,
                createdAt='2026-01-0'+str(i+1)+'T00:00:00+00:00')))
        calls = []
        # Exercise the generated chain method against a disk-backed load boundary.
        # This focused fixture checks scheduling, not the full catalog schema.
        def load(reference, candidate=None):
            calls.append(reference['path'])
            point = json.loads(read_pin(reference)) if candidate is None else candidate
            read_pin(point['content'])
            return point, {'createdAt':point['createdAt']}
        owner = SimpleNamespace(deadline=SimpleNamespace(check=lambda:None), load=load,
            config=SimpleNamespace(value={'maxChainPoints':5,'maxChainAgeSeconds':999999}))
        return lambda:namespace['chain'](owner, refs[-1]), refs, calls

    def test_each_point_loaded_once_and_next_call_revalidates(self):
        with tempfile.TemporaryDirectory() as directory:
            chain, refs, calls = self.fixture(directory)
            self.assertEqual([r[0] for r in chain()], refs)
            self.assertEqual(calls, [r['path'] for r in refs])
            chain()
            self.assertEqual(calls, [r['path'] for r in refs]*2)

    def test_changed_point_and_payload_rejected_on_next_call(self):
        for damaged in ('point2', 'payload0', 'payload2'):
            with self.subTest(damaged=damaged), tempfile.TemporaryDirectory() as directory:
                chain, _, _ = self.fixture(directory)
                chain()
                path = Path(directory)/damaged
                raw = path.read_bytes()
                path.write_bytes(bytes([raw[0]^1])+raw[1:])
                with self.assertRaisesRegex(ValueError, 'PIN_CHANGED'): chain()

    def test_actual_standard_chain_plans_without_full_load(self):
        payload, _ = standard_sources()
        tree = ast.parse(apply(payload)['common/repository_minimal.py'])
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MinimumCatalog')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'chain')
        calls = [n for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'load']
        self.assertEqual(len(calls), 1, 'current point must not be fully loaded twice')
        self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'read_pin' for n in ast.walk(method)))

if __name__ == '__main__': unittest.main()
