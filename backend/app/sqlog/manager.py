from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
from .models import Quest, QuestStatus
from .signer import QuestSigner
from .store import QuestLogStore
from datetime import datetime

class QuestLogManager:
    def __init__(self, log_path: Path):
        self.store = QuestLogStore(log_path)
        self.signer = QuestSigner()
        self._data = self.store.load()

    def _get_quest(self, quest_id: str) -> Optional[Quest]:
        for q in self._data["quests"]:
            if q["id"] == quest_id:
                return q
        return None

    def update_status(self, quest_id: str, new_status: QuestStatus, agent: str, evidence: str) -> bool:
        quest = self._get_quest(quest_id)
        if not quest:
            return False
            
        current_status = QuestStatus(quest["status"])
        
        # Enforce state machine rules
        allowed = False
        if current_status == QuestStatus.PENDING and new_status == QuestStatus.IN_PROGRESS and agent in ["generator", "human"]:
            allowed = True
        elif current_status == QuestStatus.IN_PROGRESS and new_status == QuestStatus.FAILED and agent == "tribunal":
            allowed = True
        elif current_status == QuestStatus.IN_PROGRESS and new_status == QuestStatus.CERTIFIED and agent == "tribunal":
            allowed = True
        elif current_status == QuestStatus.FAILED and new_status == QuestStatus.IN_PROGRESS and agent in ["generator", "human"]:
            allowed = True
            
        if not allowed:
            raise PermissionError(f"Transition from {current_status} to {new_status} not allowed by agent {agent}")
            
        quest["status"] = new_status.value
        quest["updated_at"] = datetime.utcnow().isoformat()
        quest["verdict"] = {"timestamp": datetime.utcnow().isoformat(), "verdict": new_status.value, "evidence": evidence}
        
        self.store.save(self._data)
        return True

    def add_quest(self, quest: Quest):
        quest_dict = asdict(quest)
        # Convert Enum status to string for serialization
        quest_dict["status"] = quest.status.value
        self._data["quests"].append(quest_dict)
        self.store.save(self._data)
