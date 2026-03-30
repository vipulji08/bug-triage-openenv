# 🐛 Bug Triage OpenEnv

> An OpenEnv-compliant environment for training AI agents on real-world software bug report triage.

---

## 🎯 What is This?

Software engineering teams receive hundreds of bug reports daily. Each report must be:
- Assigned a **priority** (critical / high / medium / low)
- Assigned a **category** (crash / security / performance / ui / other)  
- Routed to the right **team** (backend / frontend / mobile / devops / qa)
- Checked for **duplicates**
- Identified if **invalid** or **needs more info**

This environment trains AI agents to do this automatically, saving engineer time and ensuring critical bugs get fixed faster.

---

## 🗂️ Tasks

| Task | Difficulty | Bugs | Required Actions | Max Score |
|------|-----------|------|-----------------|-----------|
| `easy` | ⭐ | 5 | priority + category | 1.0 |
| `medium` | ⭐⭐ | 6 | priority + category + team + duplicate detection | 1.0 |
| `hard` | ⭐⭐⭐ | 8 | All above + invalid detection + info requests | 1.0 |

---

## 📊 Action & Observation Spaces

### Observation (what agent sees)
```python
{
  "current_bug": {
    "id": "BUG-001",
    "title": "App crashes on login",
    "description": "...",
    "reporter": "user@example.com",
    "labels": ["crash", "login"]
  },
  "inbox_count": 4,           # bugs remaining
  "triaged_count": 1,         # bugs done
  "task_goal": "Assign priority and category...",
  "available_actions": ["assign_priority", "assign_category", ...],
  "last_action_result": "✅ Good: Flagged severe bug"
}
```

### Actions (what agent can do)
```python
# Assign priority
{"action_type": "assign_priority", "value": "critical", "bug_id": "BUG-001"}

# Assign category  
{"action_type": "assign_category", "value": "security", "bug_id": "BUG-001"}

# Assign team
{"action_type": "assign_team", "value": "backend", "bug_id": "BUG-001"}

# Mark as duplicate
{"action_type": "mark_duplicate", "value": "true", "bug_id": "BUG-104"}

# Request more info
{"action_type": "request_info", "value": "true", "bug_id": "BUG-203"}

# Close as invalid
{"action_type": "close_invalid", "value": "true", "bug_id": "BUG-202"}
```

---

## 🚀 Setup & Usage

### Local Setup
```bash
# 1. Clone the repo
git clone https://huggingface.co/spaces/YOUR_USERNAME/bug-triage-openenv
cd bug-triage-openenv

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export HF_TOKEN=your_token_here
export MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
export API_BASE_URL=https://router.huggingface.co/v1

# 4. Run the server
python app.py

# 5. Run baseline inference
python inference.py
```

### Docker
```bash
docker build -t bug-triage-env .
docker run -p 7860:7860 \
  -e HF_TOKEN=your_token \
  -e MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct \
  bug-triage-env
```

### API Usage
```python
import requests

# Reset environment
resp = requests.post("http://localhost:7860/reset?task=easy")
obs = resp.json()["observation"]

# Take an action
action = {
    "action_type": "assign_priority",
    "value": "critical",
    "bug_id": "BUG-001"
}
resp = requests.post("http://localhost:7860/step", json=action)
result = resp.json()
print(result["reward"]["score"])  # 0.0 - 1.0
```

---

## 📈 Baseline Scores

| Model | Easy | Medium | Hard | Average |
|-------|------|--------|------|---------|
| meta-llama/Llama-3.1-8B-Instruct | 0.72 | 0.61 | 0.48 | 0.60 |

Run baseline: `python inference.py`

---

## 🏗️ Project Structure

```
bug-triage-openenv/
├── inference.py      # Baseline inference script (MANDATORY)
├── app.py            # FastAPI server
├── openenv.yaml      # OpenEnv spec metadata
├── Dockerfile        # Container config
├── requirements.txt  # Python deps
├── README.md         # This file
└── env/
    ├── __init__.py
    ├── environment.py # Core env: reset/step/state
    ├── models.py      # Pydantic typed models
    └── graders.py     # Task graders (scoring)
```

---

## 🎁 Reward Function

- **Immediate reward** (0.0–1.0): Heuristic signal after each action
  - High severity bug + high priority = 0.7 reward
  - Wrong priority on crash = 0.1 reward  
  - Skipping a bug = 0.05 (penalty)
  - Wrongly closing valid bug = -0.3 penalty

- **Final reward**: Exact grader score at episode end
  - Easy: avg of (priority_score + category_score) / 2
  - Medium: weighted priority(30%) + category(25%) + team(25%) + duplicate(20%)
  - Hard: all above + invalid detection + penalties for false closes
