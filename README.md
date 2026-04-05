---
title: Bug Triage OpenEnv
emoji: 🐛
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
tags:
- openenv
- reinforcement-learning
- bug-triage
pinned: false
---

# Bug Triage OpenEnv

A real-world OpenEnv environment for training AI agents on software bug report triage.

## Tasks

| Task | Bugs | Actions |
|------|------|---------|
| easy | 5 | priority + category |
| medium | 6 | priority + category + team + duplicate |
| hard | 8 | full triage + invalid + info request |

## Setup

```bash
pip install -r requirements.txt
python server/app.py
```

## Run Inference

```bash
export HFTOKEN=your_token
python inference.py
```
