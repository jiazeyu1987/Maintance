from __future__ import annotations

import importlib
from pathlib import Path


def test_spring_constructor_gate_blocks_ambiguous_bean(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.spring_constructor_contract_gate")
    source = tmp_path / "MesTeamLeaderProcessConfigServiceImpl.java"
    source.write_text(
        """
        @Service
        public class MesTeamLeaderProcessConfigServiceImpl {
            public MesTeamLeaderProcessConfigServiceImpl(Dependency dependency) {}
            MesTeamLeaderProcessConfigServiceImpl(TestDependency dependency, boolean testOnly) {}
        }
        """,
        encoding="utf-8",
    )

    failures = gate.find_constructor_contract_failures(tmp_path)

    assert len(failures) == 1
    assert failures[0]["class"] == "MesTeamLeaderProcessConfigServiceImpl"
    assert failures[0]["constructorCount"] == 2
    assert failures[0]["autowiredCount"] == 0


def test_spring_constructor_gate_accepts_explicit_autowired_constructor(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.spring_constructor_contract_gate")
    source = tmp_path / "ValidService.java"
    source.write_text(
        """
        @Service
        public class ValidService {
            @Autowired
            public ValidService(Dependency dependency) {}
            ValidService(TestDependency dependency, boolean testOnly) {}
        }
        """,
        encoding="utf-8",
    )

    assert gate.find_constructor_contract_failures(tmp_path) == []


def test_spring_constructor_gate_accepts_single_constructor_and_explicit_no_arg(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.spring_constructor_contract_gate")
    (tmp_path / "SingleService.java").write_text(
        "@Service public class SingleService { public SingleService(Dependency dependency) {} }\n",
        encoding="utf-8",
    )
    (tmp_path / "NoArgService.java").write_text(
        "@Service public class NoArgService { public NoArgService() {} "
        "NoArgService(Dependency dependency) {} }\n",
        encoding="utf-8",
    )

    assert gate.find_constructor_contract_failures(tmp_path) == []


def test_publish_script_runs_spring_constructor_gate_before_backend_build() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "ops" / "deploy" / "publish-int-ruoyi.ps1").read_text(encoding="utf-8")

    assert "spring_constructor_contract_gate.py" in script
    gate_index = script.index("Invoke-BackendSpringConstructorGate")
    backend_build_index = script.index("Info 'Building backend jar'")
    assert gate_index < backend_build_index
