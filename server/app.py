"""
server/app.py - Main server entry point
"""
import os
import uvicorn
from openenv.core.env_server import create_fastapi_app
from env.environment import BugTriageEnv
from env.models import BugTriageAction, BugTriageObservation

TASK = os.getenv("task", "easy")

app = create_fastapi_app(
    env=lambda: BugTriageEnv(task=TASK),
    action_cls=BugTriageAction,
    observation_cls=BugTriageObservation,
)

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
