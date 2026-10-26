import tomllib
import tomli_w
import os
from pathlib import Path
from typing import Dict, Any

class QuestLogStore:
    def __init__(self, log_path: Path):
        self.log_path = log_path

    def load(self) -> Dict[str, Any]:
        if not self.log_path.exists():
            return {"manifest": {}, "quests": []}
        with open(self.log_path, "rb") as f:
            return tomllib.load(f)

    def save(self, data: Dict[str, Any]):
        # Atomic write
        temp_path = self.log_path.with_suffix(".tmp")
        with open(temp_path, "wb") as f:
            tomli_w.dump(data, f)
        os.replace(temp_path, self.log_path)
