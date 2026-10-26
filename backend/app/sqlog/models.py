from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class QuestStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    FAILED = "FAILED"
    CERTIFIED = "CERTIFIED"
    CANCELED = "CANCELED"
    DEPRECATED = "DEPRECATED"

@dataclass
class Verdict:
    timestamp: str
    verdict: str
    evidence: str

@dataclass
class Quest:
    id: str
    title: str
    status: QuestStatus = QuestStatus.PENDING
    priority: str = "P1"
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: str = "generator"
    attempts: int = 0
    max_attempts: int = 3
    violations: List[str] = field(default_factory=list)
    suggested_fix: str = ""
    module: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    verdict: Dict[str, Any] = field(default_factory=dict)
    certified_at: str = ""
    certificate_hash: str = ""
