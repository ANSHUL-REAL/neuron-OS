from pathlib import Path

from neuronos.config import resolve_data_dir


def test_resolve_data_dir_uses_env_var(monkeypatch):
    monkeypatch.setenv("NEURONOS_DATA_DIR", "D:\\NeuronOS\\data")

    assert resolve_data_dir() == Path("D:/NeuronOS/data")


def test_resolve_data_dir_defaults_to_d_drive_when_available(monkeypatch):
    monkeypatch.delenv("NEURONOS_DATA_DIR", raising=False)

    assert resolve_data_dir(drive_exists=lambda drive: drive == "D:/") == Path(
        "D:/NeuronOS/data"
    )
