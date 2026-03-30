"""
environment.py - Official OpenEnv Environment
Inherits from openenv.core.env_server.interfaces.Environment

API:
  reset(seed, episode_id) -> BugTriageObservation
  step(action)            -> BugTriageObservation
  state()                 -> BugTriageState
"""

import uuid
from typing import Optional, Any
from openenv.core.env_server.interfaces import Environment

from env.models import BugTriageObservation, BugTriageAction, BugTriageState
from env.graders import (
    grade_easy_task, grade_medium_task, grade_hard_task,
    EASY_GROUND_TRUTH, MEDIUM_GROUND_TRUTH, HARD_GROUND_TRUTH
)

# ============================================================
# BUG DATA
# ============================================================
EASY_BUGS = [
    {"id": "BUG-001", "title": "App crashes on login",
     "description": "Every time I click login button the app crashes immediately. Reproducible 100%.",
     "reporter": "user@example.com", "created_at": "2024-01-15", "labels": ["crash", "login"]},
    {"id": "BUG-002", "title": "Button color slightly off",
     "description": "Submit button is #2196F3 instead of #1976D2. Minor visual issue.",
     "reporter": "design@example.com", "created_at": "2024-01-15", "labels": ["ui", "cosmetic"]},
    {"id": "BUG-003", "title": "Dashboard loads slowly",
     "description": "Dashboard takes 8-10 seconds to load. Gets worse with more data.",
     "reporter": "power_user@example.com", "created_at": "2024-01-16", "labels": ["performance"]},
    {"id": "BUG-004", "title": "SQL injection possible in search",
     "description": "Search field does not sanitize input. I was able to inject SQL and see user table.",
     "reporter": "security@example.com", "created_at": "2024-01-16", "labels": ["security"]},
    {"id": "BUG-005", "title": "Typo in welcome message",
     "description": "Welcome message says 'Wellcome' instead of 'Welcome' on home page.",
     "reporter": "qa@example.com", "created_at": "2024-01-17", "labels": ["ui", "typo"]},
]

MEDIUM_BUGS = [
    {"id": "BUG-101", "title": "API endpoint exposes admin tokens",
     "description": "GET /api/users returns auth tokens in response body for admin accounts.",
     "reporter": "pentest@example.com", "created_at": "2024-02-01", "labels": ["security", "api"]},
    {"id": "BUG-102", "title": "Modal dialog not closing on mobile",
     "description": "On iOS Safari, close button on modals does not respond to tap.",
     "reporter": "mobile_user@example.com", "created_at": "2024-02-01", "labels": ["mobile", "ui"]},
    {"id": "BUG-103", "title": "App freezes uploading large file",
     "description": "Uploading files over 50MB causes mobile app to freeze and require force-quit.",
     "reporter": "field_agent@example.com", "created_at": "2024-02-02", "labels": ["crash", "mobile"]},
    {"id": "BUG-104", "title": "Dark mode text hard to read",
     "description": "Low contrast in dark mode. Reported last week as BUG-089, same issue.",
     "reporter": "accessibility@example.com", "created_at": "2024-02-02", "labels": ["ui", "dark-mode"]},
    {"id": "BUG-105", "title": "Memory leak in background worker",
     "description": "Background sync worker grows to 2GB+ RAM over 24hrs, needs restart.",
     "reporter": "devops@example.com", "created_at": "2024-02-03", "labels": ["performance", "memory"]},
    {"id": "BUG-106", "title": "Null pointer in payment processing",
     "description": "NullPointerException thrown when user has no saved payment method at checkout.",
     "reporter": "support@example.com", "created_at": "2024-02-03", "labels": ["crash", "payment"]},
]

HARD_BUGS = [
    {"id": "BUG-201", "title": "CSRF token not validated on password change",
     "description": "POST /account/password does not validate CSRF token. Allows cross-site forgery.",
     "reporter": "security_researcher@example.com", "created_at": "2024-03-01", "labels": ["security"]},
    {"id": "BUG-202", "title": "App slow when I use it",
     "description": "Sometimes the app feels slow. No steps to reproduce. Using Chrome.",
     "reporter": "random_user@example.com", "created_at": "2024-03-01", "labels": []},
    {"id": "BUG-203", "title": "Database queries slow after migration",
     "description": "After DB migration some queries are 10x slower. Need query plans to investigate.",
     "reporter": "dba@example.com", "created_at": "2024-03-02", "labels": ["performance", "database"]},
    {"id": "BUG-204", "title": "Race condition causes data corruption",
     "description": "Concurrent writes to user profile can corrupt data. Seen in load tests at 1000+ rps.",
     "reporter": "qa_lead@example.com", "created_at": "2024-03-02", "labels": ["crash", "concurrency"]},
    {"id": "BUG-205", "title": "Dropdown overflows on small screens",
     "description": "On 320px wide screens, category dropdown extends beyond viewport.",
     "reporter": "ux@example.com", "created_at": "2024-03-03", "labels": ["ui", "responsive"]},
    {"id": "BUG-206", "title": "JWT secret hardcoded in config",
     "description": "Found JWT_SECRET='mysecret123' in config.py committed to git repo.",
     "reporter": "devops_sec@example.com", "created_at": "2024-03-03", "labels": ["security"]},
    {"id": "BUG-207", "title": "Export to CSV missing some records",
     "description": "CSV export seems to skip some records. Hard to tell exact count without knowing filters.",
     "reporter": "analyst@example.com", "created_at": "2024-03-04", "labels": ["export"]},
    {"id": "BUG-208", "title": "OOM crash on large dataset",
     "description": "Processing datasets over 1M rows causes OutOfMemoryError and server restart.",
     "reporter": "data_team@example.com", "created_at": "2024-03-04", "labels": ["crash", "memory"]},
]

TASK_BUGS = {"easy": EASY_BUGS, "medium": MEDIUM_BUGS, "hard": HARD_BUGS}
TASK_GRADERS = {"easy": grade_easy_task, "medium": grade_medium_task, "hard": grade_hard_task}

VALID_ACTIONS = {
    "assign_priority": ["critical", "high", "medium", "low"],
    "assign_category": ["crash", "ui", "performance", "security", "other"],
    "assign_team":     ["backend", "frontend", "mobile", "devops", "qa"],
    "mark_duplicate":  ["true"],
    "request_info":    ["true"],
    "close_invalid":   ["true"],
    "skip":            ["true"],
}

TASK_GOALS = {
    "easy":   "Assign correct PRIORITY and CATEGORY to each bug report.",
    "medium": "Assign PRIORITY, CATEGORY, TEAM and detect DUPLICATES for each bug.",
    "hard":   "Fully triage: priority, category, team, detect invalid reports, request info when needed.",
}


class BugTriageEnv(Environment):
    """
    Bug Report Triage OpenEnv Environment
    Official spec compliant - inherits from openenv.core Environment

    Usage:
        env = BugTriageEnv(task="easy")
        obs = env.reset()
        obs = env.step(BugTriageAction(action_type="assign_priority", value="critical", bug_id="BUG-001"))
        state = env.state()
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self, task: str = "easy"):
        assert task in ["easy", "medium", "hard"], f"task must be easy/medium/hard"
        self.task = task
        self._state: Optional[BugTriageState] = None

    # ----------------------------------------------------------
    # reset() - Episode fresh start
    # ----------------------------------------------------------
    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None, **kwargs) -> BugTriageObservation:
        bugs = TASK_BUGS[self.task]
        eid = episode_id or str(uuid.uuid4())[:8]
        self._state = BugTriageState(
            task_id=f"{self.task}-{eid}",
            task_name=f"Bug Triage - {self.task.capitalize()}",
            difficulty=self.task,
            all_bugs=bugs.copy(),
            current_bug_index=0,
            actions_taken=[],
            total_reward=0.0,
            step_count=0,
            is_done=False,
            final_score=None,
        )
        return self._make_obs()

    # ----------------------------------------------------------
    # step() - One action
    # ----------------------------------------------------------
    def step(self, action: BugTriageAction, timeout_s: Optional[float] = None, **kwargs) -> BugTriageObservation:
        if self._state is None:
            raise RuntimeError("Call reset() first!")
        if self._state.is_done:
            raise RuntimeError("Episode done. Call reset().")

        self._state.step_count += 1
        current_bug = self._current_bug()

        # Validate
        valid, err = self._validate(action)
        if not valid:
            return self._make_obs(last_result=f"❌ Invalid action: {err}")

        # Record action
        bug_id = action.bug_id or (current_bug["id"] if current_bug else None)
        self._state.actions_taken.append({
            "step": self._state.step_count,
            "bug_id": bug_id,
            "action_type": action.action_type,
            "value": action.value,
            "reasoning": action.reasoning,
        })

        # Immediate reward feedback
        feedback = self._immediate_feedback(action, current_bug)
        self._state.total_reward += 0.3

        # Advance bug on finalizing actions
        finalizing = {"mark_duplicate", "request_info", "close_invalid", "skip"}
        if action.action_type in finalizing:
            self._state.current_bug_index += 1
        elif action.action_type == "assign_category" and self.task == "easy":
            self._state.current_bug_index += 1
        elif action.action_type == "assign_team" and self.task in ["medium", "hard"]:
            self._state.current_bug_index += 1

        # Check done
        if self._state.current_bug_index >= len(self._state.all_bugs):
            self._state.is_done = True
            final_score, _ = TASK_GRADERS[self.task](self._state.actions_taken)
            self._state.final_score = final_score
            feedback += f" | ✅ Episode done! Final score: {final_score:.3f}"

        return self._make_obs(last_result=feedback)

    # ----------------------------------------------------------
    # state() - Current state
    # ----------------------------------------------------------
    def state(self) -> BugTriageState:
        if self._state is None:
            raise RuntimeError("Call reset() first!")
        return self._state

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------
    def _current_bug(self):
        if self._state and self._state.current_bug_index < len(self._state.all_bugs):
            return self._state.all_bugs[self._state.current_bug_index]
        return None

    def _make_obs(self, last_result: str = "") -> BugTriageObservation:
        bug = self._current_bug()
        remaining = len(self._state.all_bugs) - self._state.current_bug_index
        return BugTriageObservation(
            current_bug=bug,
            inbox_count=remaining,
            triaged_count=self._state.current_bug_index,
            current_step=self._state.step_count,
            last_action_result=last_result,
            task_goal=TASK_GOALS[self.task],
            available_actions=list(VALID_ACTIONS.keys()),
            session_history=[
                {"step": a["step"], "action": a["action_type"], "value": a["value"]}
                for a in self._state.actions_taken[-5:]
            ],
        )

    def _validate(self, action: BugTriageAction):
        if action.action_type not in VALID_ACTIONS:
            return False, f"Unknown action '{action.action_type}'"
        if action.value.lower() not in VALID_ACTIONS[action.action_type]:
            return False, f"Invalid value '{action.value}' for '{action.action_type}'"
        return True, ""

    def _immediate_feedback(self, action: BugTriageAction, bug) -> str:
        if not bug:
            return "Action recorded."
        desc = bug.get("description", "").lower()
        if action.action_type == "assign_priority":
            severe = any(k in desc for k in ["crash", "injection", "null pointer", "corruption", "csrf"])
            if severe and action.value in ["critical", "high"]:
                return "✅ Correct: High-severity bug flagged with high priority"
            elif severe and action.value in ["low", "medium"]:
                return "⚠️ Warning: Severe bug marked too low"
        elif action.action_type == "close_invalid":
            if len(bug.get("description", "")) < 60:
                return "✅ Reasonable: Vague report closed as invalid"
            return "⚠️ Caution: Detailed report closed as invalid"
        elif action.action_type == "request_info":
            if not bug.get("labels"):
                return "✅ Good: No labels, requesting info is correct"
        return "Action recorded."
