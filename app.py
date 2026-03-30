"""
app.py - Official OpenEnv FastAPI server using create_fastapi_app()
Deploys on HuggingFace Spaces port 7860
"""

import uvicorn
from openenv.core.env_server import create_fastapi_app
from env.environment import BugTriageEnv
from env.models import BugTriageAction, BugTriageObservation

# Task from env var (default: easy)
import os
TASK = os.getenv("TASK", "easy")

# Official way: create_fastapi_app() from openenv-core
app = create_fastapi_app(
    env=lambda: BugTriageEnv(task=TASK),
    action_cls=BugTriageAction,
    observation_cls=BugTriageObservation,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
