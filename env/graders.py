"""
graders.py - Task graders that score agent performance
Each grader scores 0.0 to 1.0
"""

from typing import Dict, Any, Tuple


# ============================================================
# GROUND TRUTH - Correct answers for each bug
# ============================================================

EASY_GROUND_TRUTH = {
    "BUG-001": {"priority": "critical", "category": "crash",       "team": "backend"},
    "BUG-002": {"priority": "low",      "category": "ui",          "team": "frontend"},
    "BUG-003": {"priority": "medium",   "category": "performance", "team": "backend"},
    "BUG-004": {"priority": "high",     "category": "security",    "team": "backend"},
    "BUG-005": {"priority": "low",      "category": "ui",          "team": "frontend"},
}

MEDIUM_GROUND_TRUTH = {
    "BUG-101": {"priority": "high",     "category": "security",    "team": "backend",  "duplicate": False},
    "BUG-102": {"priority": "medium",   "category": "ui",          "team": "frontend", "duplicate": False},
    "BUG-103": {"priority": "critical", "category": "crash",       "team": "mobile",   "duplicate": False},
    "BUG-104": {"priority": "low",      "category": "other",       "team": "qa",       "duplicate": True},
    "BUG-105": {"priority": "medium",   "category": "performance", "team": "devops",   "duplicate": False},
    "BUG-106": {"priority": "high",     "category": "crash",       "team": "backend",  "duplicate": False},
}

HARD_GROUND_TRUTH = {
    "BUG-201": {"priority": "critical", "category": "security",    "team": "backend",  "needs_info": False, "invalid": False},
    "BUG-202": {"priority": "low",      "category": "other",       "team": "qa",       "needs_info": False, "invalid": True},
    "BUG-203": {"priority": "high",     "category": "performance", "team": "devops",   "needs_info": True,  "invalid": False},
    "BUG-204": {"priority": "critical", "category": "crash",       "team": "mobile",   "needs_info": False, "invalid": False},
    "BUG-205": {"priority": "medium",   "category": "ui",          "team": "frontend", "needs_info": False, "invalid": False},
    "BUG-206": {"priority": "high",     "category": "security",    "team": "backend",  "needs_info": False, "invalid": False},
    "BUG-207": {"priority": "low",      "category": "ui",          "team": "frontend", "needs_info": True,  "invalid": False},
    "BUG-208": {"priority": "critical", "category": "crash",       "team": "backend",  "needs_info": False, "invalid": False},
}


# ============================================================
# PRIORITY SCORE - Partial credit for close answers
# ============================================================
PRIORITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1}

def score_priority(predicted: str, actual: str) -> float:
    """Give partial credit for close priority guesses"""
    if predicted == actual:
        return 1.0
    pred_level = PRIORITY_LEVELS.get(predicted, 0)
    actual_level = PRIORITY_LEVELS.get(actual, 0)
    diff = abs(pred_level - actual_level)
    if diff == 1:
        return 0.5   # One level off = 50% credit
    elif diff == 2:
        return 0.2   # Two levels off = 20% credit
    return 0.0        # Three+ levels off = no credit


# ============================================================
# TASK 1 (EASY) - Just assign priority + category
# ============================================================
def grade_easy_task(actions_taken: list) -> Tuple[float, Dict]:
    """
    Easy task: Correctly assign priority and category to 5 bugs.
    Score = average of (priority_score + category_score) / 2 per bug
    """
    if not actions_taken:
        return 0.0, {"error": "No actions taken"}

    bug_scores = {}
    
    # Group actions by bug_id
    bug_actions: Dict[str, Dict] = {}
    for action in actions_taken:
        bug_id = action.get("bug_id")
        action_type = action.get("action_type")
        value = action.get("value", "").lower()
        if bug_id:
            if bug_id not in bug_actions:
                bug_actions[bug_id] = {}
            bug_actions[bug_id][action_type] = value

    total_score = 0.0
    graded_bugs = 0

    for bug_id, truth in EASY_GROUND_TRUTH.items():
        taken = bug_actions.get(bug_id, {})
        
        # Score priority
        pred_priority = taken.get("assign_priority", "")
        p_score = score_priority(pred_priority, truth["priority"])
        
        # Score category (exact match)
        pred_category = taken.get("assign_category", "")
        c_score = 1.0 if pred_category == truth["category"] else 0.0
        
        bug_score = (p_score + c_score) / 2.0
        bug_scores[bug_id] = {
            "priority_score": p_score,
            "category_score": c_score,
            "combined": bug_score
        }
        total_score += bug_score
        graded_bugs += 1

    final_score = total_score / max(graded_bugs, 1)
    return round(final_score, 3), bug_scores


# ============================================================
# TASK 2 (MEDIUM) - Priority + Category + Team + Duplicates
# ============================================================
def grade_medium_task(actions_taken: list) -> Tuple[float, Dict]:
    """
    Medium task: Assign priority, category, team AND detect duplicates.
    Score = weighted average per bug
    """
    if not actions_taken:
        return 0.0, {"error": "No actions taken"}

    bug_actions: Dict[str, Dict] = {}
    for action in actions_taken:
        bug_id = action.get("bug_id")
        action_type = action.get("action_type")
        value = action.get("value", "").lower()
        if bug_id:
            if bug_id not in bug_actions:
                bug_actions[bug_id] = {}
            bug_actions[bug_id][action_type] = value

    total_score = 0.0
    bug_scores = {}

    for bug_id, truth in MEDIUM_GROUND_TRUTH.items():
        taken = bug_actions.get(bug_id, {})
        
        p_score = score_priority(taken.get("assign_priority", ""), truth["priority"])
        c_score = 1.0 if taken.get("assign_category", "") == truth["category"] else 0.0
        t_score = 1.0 if taken.get("assign_team", "") == truth["team"] else 0.0
        
        # Duplicate detection
        marked_dup = "mark_duplicate" in taken
        d_score = 1.0 if marked_dup == truth["duplicate"] else 0.0
        
        # Weighted: priority 30%, category 25%, team 25%, duplicate 20%
        bug_score = (p_score * 0.30 + c_score * 0.25 + t_score * 0.25 + d_score * 0.20)
        bug_scores[bug_id] = {
            "priority": p_score, "category": c_score,
            "team": t_score, "duplicate": d_score, "combined": bug_score
        }
        total_score += bug_score

    final_score = total_score / max(len(MEDIUM_GROUND_TRUTH), 1)
    return round(final_score, 3), bug_scores


# ============================================================
# TASK 3 (HARD) - All of above + needs_info + invalid detection
# ============================================================
def grade_hard_task(actions_taken: list) -> Tuple[float, Dict]:
    """
    Hard task: Full triage including invalid bugs and info requests.
    Penalty for marking valid bugs as invalid.
    """
    if not actions_taken:
        return 0.0, {"error": "No actions taken"}

    bug_actions: Dict[str, Dict] = {}
    for action in actions_taken:
        bug_id = action.get("bug_id")
        action_type = action.get("action_type")
        value = action.get("value", "").lower()
        if bug_id:
            if bug_id not in bug_actions:
                bug_actions[bug_id] = {}
            bug_actions[bug_id][action_type] = value

    total_score = 0.0
    bug_scores = {}
    penalty = 0.0

    for bug_id, truth in HARD_GROUND_TRUTH.items():
        taken = bug_actions.get(bug_id, {})

        # Check invalid/needs_info first
        marked_invalid = "close_invalid" in taken
        marked_needs_info = "request_info" in taken

        # If bug is invalid, penalize wrong triage heavily
        if truth["invalid"]:
            inv_score = 1.0 if marked_invalid else 0.0
            bug_scores[bug_id] = {"invalid_correct": inv_score}
            total_score += inv_score
            continue

        # If bug needs info before triaging
        if truth["needs_info"]:
            info_score = 1.0 if marked_needs_info else 0.5
            p_score = score_priority(taken.get("assign_priority", ""), truth["priority"]) * 0.5
            bug_score = (info_score * 0.5 + p_score * 0.5)
            bug_scores[bug_id] = {"needs_info": info_score, "priority": p_score, "combined": bug_score}
            total_score += bug_score
            continue

        # PENALTY: Marking a valid bug as invalid
        if marked_invalid and not truth["invalid"]:
            penalty += 0.3
            bug_scores[bug_id] = {"penalty": "wrongly_closed", "score": 0.0}
            continue

        p_score = score_priority(taken.get("assign_priority", ""), truth["priority"])
        c_score = 1.0 if taken.get("assign_category", "") == truth["category"] else 0.0
        t_score = 1.0 if taken.get("assign_team", "") == truth["team"] else 0.0

        # Hard task weights: priority 35%, category 30%, team 35%
        bug_score = (p_score * 0.35 + c_score * 0.30 + t_score * 0.35)
        bug_scores[bug_id] = {
            "priority": p_score, "category": c_score,
            "team": t_score, "combined": bug_score
        }
        total_score += bug_score

    raw_score = total_score / max(len(HARD_GROUND_TRUTH), 1)
    final_score = max(0.0, raw_score - penalty)
    return round(min(final_score, 1.0), 3), bug_scores
