from typing import Dict, Tuple

PRIORITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1}

EASY_TRUTH = {
    "BUG-001": {"priority": "critical", "category": "crash"},
    "BUG-002": {"priority": "low",      "category": "ui"},
    "BUG-003": {"priority": "medium",   "category": "performance"},
    "BUG-004": {"priority": "high",     "category": "security"},
    "BUG-005": {"priority": "low",      "category": "ui"},
}
MEDIUM_TRUTH = {
    "BUG-101": {"priority": "high",     "category": "security",    "team": "backend",  "duplicate": False},
    "BUG-102": {"priority": "medium",   "category": "ui",          "team": "frontend", "duplicate": False},
    "BUG-103": {"priority": "critical", "category": "crash",       "team": "mobile",   "duplicate": False},
    "BUG-104": {"priority": "low",      "category": "other",       "team": "qa",       "duplicate": True},
    "BUG-105": {"priority": "medium",   "category": "performance", "team": "devops",   "duplicate": False},
    "BUG-106": {"priority": "high",     "category": "crash",       "team": "backend",  "duplicate": False},
}
HARD_TRUTH = {
    "BUG-201": {"priority": "critical", "category": "security",    "team": "backend",  "needs_info": False, "invalid": False},
    "BUG-202": {"priority": "low",      "category": "other",       "team": "qa",       "needs_info": False, "invalid": True},
    "BUG-203": {"priority": "high",     "category": "performance", "team": "devops",   "needs_info": True,  "invalid": False},
    "BUG-204": {"priority": "critical", "category": "crash",       "team": "mobile",   "needs_info": False, "invalid": False},
    "BUG-205": {"priority": "medium",   "category": "ui",          "team": "frontend", "needs_info": False, "invalid": False},
    "BUG-206": {"priority": "high",     "category": "security",    "team": "backend",  "needs_info": False, "invalid": False},
    "BUG-207": {"priority": "low",      "category": "ui",          "team": "frontend", "needs_info": True,  "invalid": False},
    "BUG-208": {"priority": "critical", "category": "crash",       "team": "backend",  "needs_info": False, "invalid": False},
}

def score_priority(pred, actual):
    if pred == actual: return 1.0
    diff = abs(PRIORITY_LEVELS.get(pred, 0) - PRIORITY_LEVELS.get(actual, 0))
    if diff == 1: return 0.5
    if diff == 2: return 0.2
    return 0.0

def clamp(s): return max(0.01, min(0.99, round(s, 4)))

def grade_easy_task(actions_taken):
    bug_actions = {}
    for a in actions_taken:
        bid = a.get("bug_id")
        if bid:
            if bid not in bug_actions: bug_actions[bid] = {}
            bug_actions[bid][a.get("action_type")] = a.get("value","").lower()
    total = 0.0
    for bid, truth in EASY_TRUTH.items():
        taken = bug_actions.get(bid, {})
        p = score_priority(taken.get("assign_priority",""), truth["priority"])
        c = 1.0 if taken.get("assign_category","") == truth["category"] else 0.0
        total += (p + c) / 2.0
    return clamp(total / max(len(EASY_TRUTH), 1)), {}

def grade_medium_task(actions_taken):
    bug_actions = {}
    for a in actions_taken:
        bid = a.get("bug_id")
        if bid:
            if bid not in bug_actions: bug_actions[bid] = {}
            bug_actions[bid][a.get("action_type")] = a.get("value","").lower()
    total = 0.0
    for bid, truth in MEDIUM_TRUTH.items():
        taken = bug_actions.get(bid, {})
        p = score_priority(taken.get("assign_priority",""), truth["priority"])
        c = 1.0 if taken.get("assign_category","") == truth["category"] else 0.0
        t = 1.0 if taken.get("assign_team","") == truth["team"] else 0.0
        d = 1.0 if ("mark_duplicate" in taken) == truth["duplicate"] else 0.0
        total += p*0.30 + c*0.25 + t*0.25 + d*0.20
    return clamp(total / max(len(MEDIUM_TRUTH), 1)), {}

def grade_hard_task(actions_taken):
    bug_actions = {}
    for a in actions_taken:
        bid = a.get("bug_id")
        if bid:
            if bid not in bug_actions: bug_actions[bid] = {}
            bug_actions[bid][a.get("action_type")] = a.get("value","").lower()
    total = 0.0
    penalty = 0.0
    for bid, truth in HARD_TRUTH.items():
        taken = bug_actions.get(bid, {})
        if truth["invalid"]:
            total += 1.0 if "close_invalid" in taken else 0.0
            continue
        if truth["needs_info"]:
            total += 0.7 if "request_info" in taken else 0.3
            continue
        if "close_invalid" in taken:
            penalty += 0.2
            continue
        p = score_priority(taken.get("assign_priority",""), truth["priority"])
        c = 1.0 if taken.get("assign_category","") == truth["category"] else 0.0
        t = 1.0 if taken.get("assign_team","") == truth["team"] else 0.0
        total += p*0.35 + c*0.30 + t*0.35
    raw = total / max(len(HARD_TRUTH), 1) - penalty
    return clamp(raw), {}
