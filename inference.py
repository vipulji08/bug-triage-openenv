"""
inference.py - Baseline Inference Script
MANDATORY FILE - Must be in root directory.
"""

import os
import json
import sys
from openai import OpenAI
from env.environment import BugTriageEnv
from env.models import BugTriageAction

# ============================================================
# Tere HuggingFace Variables se exactly match karta hai
# MODEL_PROVIDER, HFTOKEN, APIBASEURL, task
# ============================================================
API_BASE_URL = os.getenv("APIBASEURL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HFTOKEN", "")
PROVIDER     = os.getenv("MODEL_PROVIDER", "meta-llama")
TASK         = os.getenv("task", "easy")
MODEL_NAME   = f"{PROVIDER}/Llama-3.1-8B-Instruct"

MAX_STEPS_PER_TASK = 30

SYSTEM_PROMPT = """You are an expert software engineering manager triaging bug reports.

For each bug report, respond with a JSON object:
{
  "action_type": "<assign_priority | assign_category | assign_team | mark_duplicate | request_info | close_invalid>",
  "value": "<appropriate value>",
  "bug_id": "<bug ID>",
  "reasoning": "<brief reason>"
}

Valid values:
- assign_priority: critical, high, medium, low
- assign_category: crash, ui, performance, security, other
- assign_team: backend, frontend, mobile, devops, qa
- mark_duplicate: true
- request_info: true
- close_invalid: true

Rules:
- Security bugs (injection, CSRF, tokens) → critical + security + backend
- App crashes → critical or high + crash
- UI/cosmetic → low + ui + frontend
- Memory/performance → medium + performance + devops
- Vague reports with no steps → close_invalid
- Mobile crashes → mobile team
"""


def run_task(client, task_name):
    print(f"\n{'='*50}")
    print(f"  Task: {task_name.upper()}")
    print(f"{'='*50}")

    env = BugTriageEnv(task=task_name)
    obs = env.reset()
    print(f"  Goal: {obs.task_goal}")
    print(f"  Bugs: {obs.inbox_count}")

    step = 0
    final_score = 0.0

    actions_per_bug = {
        "easy":   ["assign_priority", "assign_category"],
        "medium": ["assign_priority", "assign_category", "assign_team"],
        "hard":   ["assign_priority", "assign_category", "assign_team"],
    }

    while not env.state().is_done and step < MAX_STEPS_PER_TASK:
        current_bug = obs.current_bug
        if current_bug is None:
            break

        for action_type in actions_per_bug[task_name]:
            if env.state().is_done:
                break

            step += 1
            bug_id = current_bug["id"]

            prompt = f"""
Bug ID: {bug_id}
Title: {current_bug["title"]}
Description: {current_bug["description"]}
Labels: {current_bug.get("labels", [])}

Provide action_type = "{action_type}" for this bug.
"""
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=200,
                    response_format={"type": "json_object"},
                )
                response_text = completion.choices[0].message.content or ""
            except Exception as e:
                print(f"  [ERROR] {e}")
                response_text = json.dumps({
                    "action_type": action_type,
                    "value": "medium" if action_type == "assign_priority" else "other",
                    "bug_id": bug_id,
                })

            try:
                data = json.loads(response_text)
                action = BugTriageAction(
                    action_type=action_type,
                    value=data.get("value", "medium"),
                    bug_id=bug_id,
                    reasoning=data.get("reasoning", ""),
                )
            except Exception:
                action = BugTriageAction(
                    action_type=action_type,
                    value="medium",
                    bug_id=bug_id,
                )

            obs = env.step(action)
            print(f"  Step {step:2d} | {bug_id} | {action_type}={action.value}")

            if env.state().is_done:
                final_score = env.state().final_score or 0.0
                break

    if env.state().final_score:
        final_score = env.state().final_score

    print(f"\n  Score: {final_score:.3f}")
    return {"task": task_name, "final_score": final_score, "steps": step}


def main():
    print("\n" + "="*50)
    print("  BUG TRIAGE OPENENV - BASELINE INFERENCE")
    print("="*50)
    print(f"  API_BASE_URL   : {API_BASE_URL}")
    print(f"  MODEL_NAME     : {MODEL_NAME}")
    print(f"  MODEL_PROVIDER : {PROVIDER}")
    print(f"  TASK           : {TASK}")
    print(f"  API_KEY set    : {'Yes' if API_KEY else 'NO - Set HFTOKEN!'}")

    if not API_KEY:
        print("\n[ERROR] HFTOKEN variable set nahi hai!")
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    results = []
    for task in ["easy", "medium", "hard"]:
        try:
            result = run_task(client, task)
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] Task {task} failed: {e}")
            results.append({"task": task, "final_score": 0.0})

    print("\n" + "="*50)
    print("  FINAL SCORES")
    print("="*50)
    total = 0.0
    for r in results:
        print(f"  {r['task']:<10} {r['final_score']:.3f}")
        total += r["final_score"]
    avg = total / 3
    print(f"  {'AVERAGE':<10} {avg:.3f}")
    print("="*50)

    with open("baseline_scores.json", "w") as f:
        json.dump({
            "model": MODEL_NAME,
            "provider": PROVIDER,
            "tasks": results,
            "average": avg
        }, f, indent=2)
    print("\n  Saved: baseline_scores.json")


if __name__ == "__main__":
    main()
