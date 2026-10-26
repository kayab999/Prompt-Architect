from backend.app.sqlog.manager import QuestLogManager
from backend.app.sqlog.models import Quest, QuestStatus
from pathlib import Path

def test_sqlog():
    manager = QuestLogManager(Path("test_quest_log.toml"))
    
    # 1. Add a quest
    q1 = Quest(id="Q001", title="Implement Base Server")
    manager.add_quest(q1)
    print("Quest added.")
    
    # 2. Try valid transition: PENDING -> IN_PROGRESS
    manager.update_status("Q001", QuestStatus.IN_PROGRESS, "generator", "Starting work")
    print("Transition PENDING -> IN_PROGRESS allowed.")
    
    # 3. Try invalid transition: IN_PROGRESS -> PENDING (not in allowed list)
    try:
        manager.update_status("Q001", QuestStatus.PENDING, "generator", "Invalid test")
    except PermissionError:
        print("Invalid transition PENDING -> IN_PROGRESS blocked (Correct).")
    
    # 4. Try allowed transition: IN_PROGRESS -> CERTIFIED
    manager.update_status("Q001", QuestStatus.CERTIFIED, "tribunal", "Passed tests")
    print("Transition IN_PROGRESS -> CERTIFIED allowed.")

if __name__ == "__main__":
    test_sqlog()
