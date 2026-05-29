from __future__ import annotations

import os
from pathlib import Path
from typing import Callable


def resolve_data_dir(
    drive_exists: Callable[[str], bool] | None = None,
) -> Path:
    configured = os.environ.get("NEURONOS_DATA_DIR")
    if configured:
        return Path(configured)

    exists = drive_exists or (lambda drive: Path(drive).exists())
    if exists("D:/"):
        return Path("D:/NeuronOS/data")

    return Path.home() / ".neuronos"
