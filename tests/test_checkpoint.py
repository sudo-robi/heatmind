"""Tests for checkpoint system (utils/checkpoint.py)."""

from utils.checkpoint import Checkpoint, CheckpointManager


class TestCheckpoint:
    def test_to_dict(self):
        cp = Checkpoint(
            checkpoint_id="cp_123",
            name="test",
            timestamp="2025-01-01T00:00:00Z",
            phase="plan",
            observations={"env_params": {"heat_index": 42}},
            trace=["step1", "step2"],
            metadata={"files": ["a.py"]},
        )
        d = cp.to_dict()
        assert d["checkpoint_id"] == "cp_123"
        assert d["phase"] == "plan"
        assert d["observations"]["env_params"]["heat_index"] == 42
        assert len(d["trace"]) == 2

    def test_from_dict(self):
        data = {
            "checkpoint_id": "cp_456",
            "name": "reflect",
            "timestamp": "2025-01-01T00:00:00Z",
            "phase": "reflect",
            "observations": {"heatmap": {"max": 50}},
            "trace": [],
            "metadata": {},
        }
        cp = Checkpoint.from_dict(data)
        assert cp.checkpoint_id == "cp_456"
        assert cp.phase == "reflect"
        assert cp.observations["heatmap"]["max"] == 50


class TestCheckpointManager:
    def test_save_and_load(self):
        mgr = CheckpointManager()
        cp_id = mgr.save_checkpoint(
            name="test_cp",
            phase="plan",
            observations={"env_params": {"heat_index": 42}},
            trace=["analyzed"],
        )
        loaded = mgr.load_checkpoint(cp_id)
        assert loaded is not None
        assert loaded.name == "test_cp"
        assert loaded.observations["env_params"]["heat_index"] == 42
        assert loaded.trace == ["analyzed"]

    def test_list_checkpoints(self):
        mgr = CheckpointManager()
        mgr.save_checkpoint(name="cp1", phase="plan", observations={}, trace=[])
        mgr.save_checkpoint(name="cp2", phase="reflect", observations={}, trace=[])
        cps = mgr.list_checkpoints()
        assert len(cps) >= 2
        names = [c["name"] for c in cps]
        assert "cp1" in names
        assert "cp2" in names

    def test_rollback_to(self):
        mgr = CheckpointManager()
        cp_id = mgr.save_checkpoint(
            name="rollback_test",
            phase="plan",
            observations={"key": "value"},
            trace=["step"],
            metadata={"test": True},
        )
        data = mgr.rollback_to(cp_id)
        assert data is not None
        assert data["phase"] == "plan"
        assert data["observations"]["key"] == "value"
        assert data["metadata"]["test"] is True

    def test_rollback_nonexistent(self):
        mgr = CheckpointManager()
        data = mgr.rollback_to("cp_nonexistent")
        assert data is None

    def test_auto_checkpoint(self):
        mgr = CheckpointManager()
        cp_id = mgr.auto_checkpoint("synthesize", {"data": 1}, ["trace1"])
        loaded = mgr.load_checkpoint(cp_id)
        assert loaded is not None
        assert loaded.phase == "synthesize"
        assert loaded.metadata.get("auto") is True

    def test_load_nonexistent(self):
        mgr = CheckpointManager()
        assert mgr.load_checkpoint("cp_does_not_exist") is None

    def test_save_with_metadata(self):
        mgr = CheckpointManager()
        cp_id = mgr.save_checkpoint(
            name="meta",
            phase="plan",
            observations={},
            trace=[],
            metadata={"files_changed": ["a.py", "b.py"], "tests_pass": True},
        )
        loaded = mgr.load_checkpoint(cp_id)
        assert loaded.metadata["files_changed"] == ["a.py", "b.py"]
        assert loaded.metadata["tests_pass"] is True
