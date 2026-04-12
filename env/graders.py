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
    if pred == actual: return 0.95  # NOT 1.0 — always keep below 1
    diff = abs(PRIORITY_LEVELS.get(pred, 0) - PRIORITY_LEVELS.get(actual, 0))
    if diff == 1: return 0.5
    if diff == 2: return 0.2
    return 0.05

def clamp(s):
    """STRICTLY between 0 and 1 — never 0.0, never 1.0"""
    s = float(s)
    if s <= 0.0: return 0.01
    if s >= 1.0: return 0.99
    return round(s, 4)

def grade_easy_task(actions_taken):
    bug_actions = {}
    for a in actions_taken:
        bid = a.get("bug_id")
        if bid:
            if bid not in bug_actions:
                bug_actions[bid] = {}
            bug_actions[bid][a.get("action_type")] = a.get("value", "").lower()

    total = 0.0
    count = len(EASY_TRUTH)
    for bid, truth in EASY_TRUTH.items():
        taken = bug_actions.get(bid, {})
        p = score_priority(taken.get("assign_priority", ""), truth["priority"])
        c = 0.95 if taken.get("assign_category", "") == truth["category"] else 0.05
        total += (p + c) / 2.0

    raw = total / max(count, 1)
    return clamp(raw), {}

def grade_medium_task(actions_taken):
    bug_actions = {}
    for a in actions_taken:
        bid = a.get("bug_id")
        if bid:
            if bid not in bug_actions:
                bug_actions[bid] = {}
            bug_actions[bid][a.get("action_type")] = a.get("value", "").lower()

    total = 0.0
    count = len(MEDIUM_TRUTH)
    for bid, truth in MEDIUM_TRUTH.items():
        taken = bug_actions.get(bid, {})
        p = score_priority(taken.get("assign_priority", ""), truth["priority"])
        c = 0.95 if taken.get("assign_category", "") == truth["category"] else 0.05
        t = 0.95 if taken.get("assign_team", "") == truth["team"] else 0.05
        d = 0.95 if ("mark_duplicate" in taken) == truth["duplicate"] else 0.05
        total += p * 0.30 + c * 0.25 + t * 0.25 + d * 0.20

    raw = total / max(count, 1)
    return clamp(raw), {}

def grade_hard_task(actions_taken):
    bug_actions = {}
    for a in actions_taken:
        bid = a.get("bug_id")
        if bid:
            if bid not in bug_actions:
                bug_actions[bid] = {}
            bug_actions[bid][a.get("action_type")] = a.get("value", "").lower()

    total = 0.0
    penalty = 0.0
    count = len(HARD_TRUTH)

    for bid, truth in HARD_TRUTH.items():
        taken = bug_actions.get(bid, {})
        if truth["invalid"]:
            total += 0.95 if "close_invalid" in taken else 0.05
            continue
        if truth["needs_info"]:
            total += 0.7 if "request_info" in taken else 0.3
            continue
        if "close_invalid" in taken:
            penalty += 0.2
            continue
        p = score_priority(taken.get("assign_priority", ""), truth["priority"])
        c = 0.95 if taken.get("assign_category", "") == truth["category"] else 0.05
        t = 0.95 if taken.get("assign_team", "") == truth["team"] else 0.05
        total += p * 0.35 + c * 0.30 + t * 0.35

    raw = (total / max(count, 1)) - penalty
    return clamp(raw), {}
