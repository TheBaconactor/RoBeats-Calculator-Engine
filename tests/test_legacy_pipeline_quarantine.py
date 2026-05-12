import subprocess
import sys
import types
from pathlib import Path


def test_task_execution_import_does_not_load_legacy_song_processor():
    repo_root = Path(__file__).resolve().parents[1]
    script = (
        "import sys\n"
        "import gear_optimizer.task_execution\n"
        "print('gear_optimizer.pipeline.song_processor' in sys.modules)\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "False"


def test_legacy_song_processor_adapter_is_lazy_and_delegates(monkeypatch):
    import gear_optimizer.legacy.song_processor_adapter as adapter

    calls = []
    fake_module = types.ModuleType("gear_optimizer.pipeline.song_processor")
    fake_module.safe_process_song_task = lambda task: calls.append(task) or {"ok": True, "task": task}

    monkeypatch.setitem(sys.modules, "gear_optimizer.pipeline.song_processor", fake_module)

    assert adapter.safe_process_song_task(("song",)) == {"ok": True, "task": ("song",)}
    assert calls == [("song",)]
