"""
inference.py - Baseline Inference Script
MANDATORY FILE - Must be in root directory.
"""

import os
import json
import sys

# ============================================================
# Config from environment variables
# ============================================================
API_BASE_URL   = os.getenv("APIBASEURL", os.getenv("API_BASE_URL", "https://router.huggingface.co/v1"))
API_KEY        = os.getenv("HFTOKEN", os.getenv("HF_TOKEN", os.getenv("API_KEY", "")))
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "meta-llama")
MODEL_NAME     = os.getenv("MODELNAME", os.getenv("MODEL_NAME", f"{MODEL_PROVIDER}/Llama-3.1-8B-Instruct"))
TASK           = os.getenv("task", "easy")

MAX_STEPS = 30

SYSTEM_PROMPT = """You are an expert software engineering manager triaging bug reports.

Respond with ONLY a JSON object like this:
{
  "action_type": "assign_priority",
  "value": "critical",
  "bug_id": "BUG-001",
  "reasoning": "App crashes are critical"
}

Valid action_type values:
- assign_priority: values = critical, high, medium, low
- assign_category: values = crash, ui, performance, security, other
- assign_team: values = backend, frontend, mobile, devops, qa
- mark_duplicate: values = true
- request_info: values = true
- close_invalid: values = true

Rules:
- Security bugs → critical + security + backend
- App crashes → critical or high
- UI issues → low + frontend
- Performance → medium + devops
- Vague reports → close_invalid
- Mobile crashes → mobile team
"""

def get_client():
    try:
        from openai import OpenAI
        return OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "dummy")
    except Exception as e:
        print(f"[ERROR] OpenAI client failed: {e}")
        return None

def run_task(client, task_name):
    try:
        from env.environment import BugTriageEnv
        from env.models import BugTriageAction
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return {"task": task_name, "final_score": 0.0, "error": str(e)}

    print(f"\n{'='*50}")
    print(f"  Task: {task_name.upper()}")
    print(f"{'='*50}")

    try:
        env = BugTriageEnv(task=task_name)
        obs = env.reset()
        print(f"  Goal: {obs.task_goal}")
        print(f"  Bugs: {obs.inbox_count}")
    except Exception as e:
        print(f"[ERROR] Env init failed: {e}")
        return {"task": task_name, "final_score": 0.0, "error": str(e)}

    step = 0
    final_score = 0.0

    actions_per_bug = {
        "easy":   ["assign_priority", "assign_category"],
        "medium": ["assign_priority", "assign_category", "assign_team"],
        "hard":   ["assign_priority", "assign_category", "assign_team"],
    }

    try:
        while not env.state().is_done and step < MAX_STEPS:
            current_bug = obs.current_bug
            if current_bug is None:
                break

            for action_type in actions_per_bug.get(task_name, ["assign_priority"]):
                if env.state().is_done:
                    break

                step += 1
                bug_id = current_bug.get("id", "BUG-001")

                # Default fallback values
                fallback_values = {
                    "assign_priority": "medium",
                    "assign_category": "other",
                    "assign_team": "backend",
                    "mark_duplicate": "true",
                    "request_info": "true",
                    "close_invalid": "true",
                }

                action_value = fallback_values.get(action_type, "medium")

                # Try LLM if client available and API key set
                if client and API_KEY:
                    try:
                        prompt = f"""
Bug ID: {bug_id}
Title: {current_bug.get('title', '')}
Description: {current_bug.get('description', '')}
Labels: {current_bug.get('labels', [])}

Provide ONLY action_type="{action_type}" as JSON.
"""
                        completion = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": prompt},
                            ],
                            temperature=0.1,
                            max_tokens=150,
                        )
                        response_text = completion.choices[0].message.content or ""

                        # Parse response
                        text = response_text.strip()
                        if "```" in text:
                            text = text.split("```")[1] if "```json" not in text else text.split("```json")[1].split("```")[0]
                        
                        data = json.loads(text.strip())
                        action_value = str(data.get("value", action_value)).lower()

                    except Exception as e:
                        print(f"  [WARN] LLM call failed, using fallback: {e}")
                        action_value = fallback_values.get(action_type, "medium")

                try:
                    from env.models import BugTriageAction
                    action = BugTriageAction(
                        action_type=action_type,
                        value=action_value,
                        bug_id=bug_id,
                        reasoning="automated triage",
                    )
                    obs = env.step(action)
                    print(f"  Step {step:2d} | {bug_id} | {action_type}={action_value}")
                except Exception as e:
                    print(f"  [WARN] Step failed: {e}")
                    break

                if env.state().is_done:
                    break

        final_score = env.state().final_score or 0.0

    except Exception as e:
        print(f"[ERROR] Task loop failed: {e}")
        try:
            final_score = env.state().final_score or 0.0
        except:
            final_score = 0.0

    print(f"\n  Score: {final_score:.3f}")
    return {"task": task_name, "final_score": round(final_score, 3), "steps": step}


def main():
    print("\n" + "="*50)
    print("  BUG TRIAGE OPENENV - BASELINE INFERENCE")
    print("="*50)
    print(f"  API_BASE_URL   : {API_BASE_URL}")
    print(f"  MODEL_NAME     : {MODEL_NAME}")
    print(f"  API_KEY set    : {'Yes' if API_KEY else 'No (using fallback)'}")
    print(f"  TASK           : {TASK}")

    # Get client (won't crash if fails)
    client = get_client()

    results = []
    for task in ["easy", "medium", "hard"]:
        try:
            result = run_task(client, task)
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] Task {task} failed: {e}")
            results.append({"task": task, "final_score": 0.0, "error": str(e)})

    # Print scores
    print("\n" + "="*50)
    print("  FINAL SCORES")
    print("="*50)
    total = 0.0
    for r in results:
        score = r.get("final_score", 0.0)
        total += score
        print(f"  {r['task']:<10} {score:.3f}")

    avg = total / max(len(results), 1)
    print(f"  {'AVERAGE':<10} {avg:.3f}")
    print("="*50)

    # Save results
    try:
        output = {
            "model": MODEL_NAME,
            "provider": MODEL_PROVIDER,
            "tasks": results,
            "average": round(avg, 3)
        }
        with open("baseline_scores.json", "w") as f:
            json.dump(output, f, indent=2)
        print("\n  Saved: baseline_scores.json")
    except Exception as e:
        print(f"  [WARN] Could not save scores: {e}")

    print("\n  Inference complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
