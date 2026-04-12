from typing import Optional, List, Dict, Any
from openenv.core.env_server.types import Action, Observation, State

class BugTriageObservation(Observation):
    current_bug: Optional[Dict[str, Any]] = None
    inbox_count: int = 0
    triaged_count: int = 0
    current_step: int = 0
    last_action_result: str = ""
    task_goal: str = ""
    available_actions: List[str] = []
    session_history: List[Dict[str, Any]] = []

class BugTriageAction(Action):
    action_type: str
    value: str
    bug_id: Optional[str] = None
    reasoning: Optional[str] = None

class BugTriageState(State):
    task_id: str
    task_name: str
    difficulty: str
    all_bugs: List[Dict[str, Any]] = []
    current_bug_index: int = 0
    actions_taken: List[Dict[str, Any]] = []
    total_reward: float = 0.0
    step_count: int = 0
    is_done: bool = False
    final_score: Optional[float] = None
