from __future__ import annotations

import json
from typing import Any

from .planner import make_plan


def _llm_answer(client: Any, model: str, user_text: str, observations: list[dict[str, Any]]) -> str:
    context = "\n".join(
        f"Step {i+1}: {json.dumps(obs, ensure_ascii=False)}" for i, obs in enumerate(observations)
    )
    prompt = (
        "You are Jarvis. Provide a concise answer using observations when available.\n"
        f"User: {user_text}\n"
        f"Observations:\n{context}\n"
        "Respond in 1-3 short sentences."
    )

    try:
        out = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Be concise and accurate."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=180,
        )
        return (out.choices[0].message.content or "").strip() or "I could not produce an answer."
    except Exception as exc:
        return f"I could not produce an answer right now ({exc})."


def run_agent_task(
    user_text: str,
    intent: str,
    *,
    client: Any,
    llm_model: str,
    tools: dict[str, Any],
    max_steps: int = 4,
    replan_enabled: bool = True,
    use_llm_planner: bool = True,
    logger: Any = None,
    response_max_lines: int = 2,
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    steps = make_plan(
        user_text,
        intent,
        client=client,
        model=llm_model,
        use_llm_planner=use_llm_planner,
    )

    if logger is not None:
        logger.info("[agent] initial_plan=%s", steps)

    step_index = 0
    while step_index < min(max_steps, 12):
        if step_index >= len(steps):
            if replan_enabled:
                steps.append({"action": "llm", "prompt": user_text, "final": True})
            else:
                break

        step = steps[step_index] or {}
        action = str(step.get("action", "llm")).strip().lower()
        final_step = bool(step.get("final", False))

        if action == "tool":
            tool_name = str(step.get("tool", "")).strip()
            params = step.get("params") if isinstance(step.get("params"), dict) else {}
            tool_fn = tools.get(tool_name)

            if tool_fn is None:
                obs = {"status": "error", "tool": tool_name, "output": f"tool not found: {tool_name}"}
            else:
                try:
                    result = tool_fn(params)
                    obs = {
                        "status": str(result.get("status", "ok")),
                        "tool": tool_name,
                        "output": str(result.get("output", "")),
                    }
                except Exception as exc:
                    obs = {"status": "error", "tool": tool_name, "output": f"tool error: {exc}"}

            observations.append(obs)
            if logger is not None:
                logger.info("[agent] observation=%s", obs)

            if final_step:
                if obs.get("status") == "ok":
                    output = obs.get("output", "Done.")
                    # Enforce response line limit
                    if response_max_lines > 0:
                        lines = output.split("\n")
                        output = "\n".join(lines[:response_max_lines])
                    return {
                        "response": output,
                        "observations": observations,
                        "plan": steps,
                    }
                if replan_enabled:
                    steps.append({"action": "llm", "prompt": user_text, "final": True})

        else:
            reply = _llm_answer(client, llm_model, user_text, observations)
            # Enforce response line limit
            if response_max_lines > 0:
                lines = reply.split("\n")
                reply = "\n".join(lines[:response_max_lines])
            return {
                "response": reply,
                "observations": observations,
                "plan": steps,
            }

        step_index += 1

    reply = _llm_answer(client, llm_model, user_text, observations)
    # Enforce response line limit
    if response_max_lines > 0:
        lines = reply.split("\n")
        reply = "\n".join(lines[:response_max_lines])
    return {"response": reply, "observations": observations, "plan": steps}
