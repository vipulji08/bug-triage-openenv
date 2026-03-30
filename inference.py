"""
inference.py - Baseline Inference Script
==========================================
MANDATORY FILE - Must be in root directory.

Uses OpenAI client to run an LLM agent against the Bug Triage environment.
Reads credentials from environment variables:
  API_BASE_URL  - LLM API endpoint
  MODEL_NAME    - Model to use
  HF_TOKEN      - API key

Runs all 3 tasks and prints reproducible scores.
"""

import os
import json
import sys
from openai import OpenAI
from env.environment import BugTriageEnv
from env.models import BugTriageAction

# ============================================================
# Config from environment variables (MANDATORY)
# ============================================================
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
MODEL_NAME   = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

MAX_STEPS_PER_TASK = 30  # Safety limit

SYSTEM_PROMPT = """You are an expert software engineering manager triaging bug reports.

For each bug report, you must respond with a JSON object specifying your triage decision.

Response format (JSON only, no extra text):
{
  "action_type": "<one of: assign_priority, assign_category, assign_team, mark_duplicate, request_info, close_invalid>",
  "value": "<appropriate value>",
  "bug_id": "<bug ID from the report>",
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
- Security vulnerabilities (injection, CSRF, exposed tokens) → critical + security
- Crashes that are reproducible → critical or high
- UI/cosmetic issues → low
- Memory leaks / performance → medium + performance  
- Vague reports with no reproduction steps → close_invalid or request_info
- Mobile crashes → assign to mobile team
- DB/server issues → assign to backend or devops
"""


def build_user_prompt(observation) -> str:
    """Build prompt from current observation"""
    bug = observation.current_bug
    if bug is None:
        return "No more bugs to triage."

    prompt = f"""
Goal: {observation.task_goal}

Current Bug Report:
===================
ID: {bug.id}
Title: {bug.title}
Description: {bug.description}
Reporter: {bug.reporter}
Labels: {', '.join(bug.labels) if bug.labels else 'none'}

Bugs remaining after this: {observation.inbox_count - 1}
Already triaged: {observation.triaged_count}

Previous action result: {observation.last_action_result or 'N/A'}

Respond with a single JSON triage decision for bug {bug.id}.
"""
    return prompt.strip()


def parse_llm_action(response_text: str, current_bug_id: str) -> BugTriageAction:
    """Parse LLM response into a BugTriageAction"""
    # Clean up response
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(text)
        return BugTriageAction(
            action_type=data.get("action_type", "skip"),
            value=data.get("value", "true"),
            bug_id=data.get("bug_id", current_bug_id),
            reasoning=data.get("reasoning", ""),
        )
    except (json.JSONDecodeError, Exception):
        # Fallback: if can't parse, assign medium priority
        print(f"  [WARN] Could not parse LLM response, using fallback. Response: {text[:100]}")
        return BugTriageAction(
            action_type="assign_priority",
            value="medium",
            bug_id=current_bug_id,
            reasoning="Fallback action due to parse error",
        )


def run_task(client: OpenAI, task_name: str) -> dict:
    """Run one task and return results"""
    print(f"\n{'='*50}")
    print(f"  Running Task: {task_name.upper()}")
    print(f"{'='*50}")

    env = BugTriageEnv(task=task_name)
    obs = env.reset()
    
    print(f"  Goal: {obs.task_goal}")
    print(f"  Total bugs: {obs.inbox_count}")

    step = 0
    final_score = 0.0
    all_rewards = []
    
    # For each bug, we need multiple actions (priority + category + team)
    # So we loop until done
    actions_per_bug = {
        "easy":   ["assign_priority", "assign_category"],
        "medium": ["assign_priority", "assign_category", "assign_team"],
        "hard":   ["assign_priority", "assign_category", "assign_team"],
    }

    while not env.state().is_done and step < MAX_STEPS_PER_TASK:
        current_bug = obs.current_bug
        if current_bug is None:
            break

        # For each bug, take all required actions
        required_actions = actions_per_bug[task_name]
        
        for action_type in required_actions:
            if env.state().is_done:
                break
                
            step += 1
            user_prompt = build_user_prompt(obs)
            
            # Override prompt to ask for specific action type
            specific_prompt = f"{user_prompt}\n\nNow specifically provide: action_type = '{action_type}'"

            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": specific_prompt},
                    ],
                    temperature=0.1,  # Low temperature for reproducibility
                    max_tokens=200,
                    response_format={"type": "json_object"},
                )
                response_text = completion.choices[0].message.content or ""
            except Exception as e:
                print(f"  [ERROR] LLM call failed: {e}")
                response_text = json.dumps({
                    "action_type": action_type,
                    "value": "medium" if action_type == "assign_priority" else "other",
                    "bug_id": current_bug.id,
                })

            action = parse_llm_action(response_text, current_bug.id)
            action.action_type = action_type  # Ensure correct action type
            
            obs, reward, done, info = env.step(action)
            all_rewards.append(reward.score)

            print(f"  Step {step:2d} | Bug {current_bug.id} | {action_type}={action.value} | reward={reward.score:.3f}")
            
            if reward.feedback:
                print(f"           Feedback: {reward.feedback[:80]}")

            if done:
                final_score = env.state().final_score or reward.score
                break

        if env.state().is_done:
            final_score = env.state().final_score or final_score
            break

    avg_step_reward = sum(all_rewards) / max(len(all_rewards), 1)
    print(f"\n  ✅ Task {task_name.upper()} complete!")
    print(f"     Final Score:       {final_score:.3f}")
    print(f"     Avg Step Reward:   {avg_step_reward:.3f}")
    print(f"     Total Steps:       {step}")

    return {
        "task": task_name,
        "final_score": final_score,
        "avg_step_reward": avg_step_reward,
        "total_steps": step,
    }


def main():
    print("\n" + "="*60)
    print("  BUG TRIAGE OPENENV - BASELINE INFERENCE")
    print("="*60)
    print(f"  API_BASE_URL : {API_BASE_URL}")
    print(f"  MODEL_NAME   : {MODEL_NAME}")
    print(f"  API_KEY set  : {'Yes' if API_KEY else 'NO - SET HF_TOKEN!'}")

    if not API_KEY:
        print("\n[ERROR] HF_TOKEN not set! Export it first:")
        print("  export HF_TOKEN=your_token_here")
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # Run all 3 tasks
    results = []
    for task in ["easy", "medium", "hard"]:
        try:
            result = run_task(client, task)
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] Task {task} failed: {e}")
            results.append({"task": task, "final_score": 0.0, "error": str(e)})

    # Print final summary
    print("\n" + "="*60)
    print("  FINAL BASELINE SCORES")
    print("="*60)
    print(f"  {'Task':<10} {'Score':>8}  {'Steps':>6}")
    print(f"  {'-'*30}")
    
    total = 0.0
    for r in results:
        score = r.get("final_score", 0.0)
        steps = r.get("total_steps", 0)
        total += score
        print(f"  {r['task']:<10} {score:>8.3f}  {steps:>6}")
    
    avg = total / len(results)
    print(f"  {'-'*30}")
    print(f"  {'AVERAGE':<10} {avg:>8.3f}")
    print("="*60)

    # Save results to JSON
    output = {"model": MODEL_NAME, "tasks": results, "average_score": avg}
    with open("baseline_scores.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to baseline_scores.json")


if __name__ == "__main__":
    main()
