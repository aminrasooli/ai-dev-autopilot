"""End-to-end demo: a supervised, noninteractive Agent SDK run for JP Autopilot.

What this demonstrates:
  - Uses the official Claude Agent SDK (`claude_agent_sdk`), not Claude Code's
    own subscription session: `env["ANTHROPIC_API_KEY"]` is set explicitly
    from this project's OWN scoped key, so the run is billed against the
    Anthropic API credits, never the Claude Code subscription.
  - Read-only tool surface: only Read/Grep/Glob are allowed. Bash, Edit,
    Write, and NotebookEdit are explicitly disallowed, so the agent cannot
    run commands, modify files, or touch git — it can only read and report.
  - Gated by our own pre-call Budget AND the SDK's native max_budget_usd as
    a second, independent ceiling.
  - Output is a plain text report the caller writes to disk itself — the
    agent never writes files directly, so there is no path for it to
    overwrite or create anything outside this one report file.
  - This script never commits, pushes, merges, or deploys anything. It is a
    read-and-report demo only, matching the "no destructive actions" rule
    for anything API-generated.

Run:
    JPAUTOPILOT_ANTHROPIC_API_KEY=sk-ant-... .venv/bin/python demos/jp_autopilot_demo.py [path-to-review]

If the project-scoped key isn't set, this prints what it WOULD do and exits
0 without making any network call — see main() below.
"""

from __future__ import annotations

import anyio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anthropic_api_kit.budget import Budget
from anthropic_api_kit.config import load_config
from anthropic_api_kit.exceptions import BudgetExhaustedError
from anthropic_api_kit.pricing import estimate_cost_usd

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

REPORT_DIR = Path(__file__).resolve().parent / "output"

READ_ONLY_TOOLS = ["Read", "Grep", "Glob"]
DISALLOWED_TOOLS = ["Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch"]


async def run_review(target_path: Path, config) -> ResultMessage | None:
    options = ClaudeAgentOptions(
        cwd=str(target_path.parent if target_path.is_file() else target_path),
        allowed_tools=READ_ONLY_TOOLS,
        disallowed_tools=DISALLOWED_TOOLS,
        permission_mode="default",
        max_turns=6,
        max_budget_usd=0.50,  # SDK-native second ceiling, independent of our own Budget
        model=config.routine_model,
        env={"ANTHROPIC_API_KEY": config.api_key()},
        system_prompt=(
            "You are a read-only code reviewer. You may only read files and "
            "search; you have no tools to edit, run commands, or write "
            "anything. Report findings as plain text — do not attempt to "
            "fix anything."
        ),
    )

    prompt = (
        f"Read {target_path.name} in the current directory and list, as "
        "plain text bullet points, up to 5 concrete correctness or security "
        "concerns worth a human's attention. Be specific about line-level "
        "behavior. Do not propose a fix, just flag the concern."
    )

    result: ResultMessage | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(message, ResultMessage):
            result = message
    return result


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent / "anthropic_api_kit" / "client.py"
    )
    config = load_config("jpautopilot", ledger_dir=str(Path(__file__).resolve().parent))
    budget = Budget(
        project_name=config.project_name,
        monthly_budget_usd=config.monthly_budget_usd,
        ledger_path=config.ledger_path,
    )

    api_key = config.api_key()
    if not api_key:
        print(
            f"[blocked] {config.api_key_env_var} is not set — no network call made.\n"
            "This is the owner action documented in REPORT.md: create a "
            "project-scoped API key for 'jp-autopilot' in the Console and "
            "export it as this variable before running the demo for real."
        )
        return 0

    try:
        budget.check_before_call(
            estimate_cost_usd(config.routine_model, input_tokens=2000, output_tokens=config.max_output_tokens)
        )
    except BudgetExhaustedError as exc:
        print(f"[blocked] {exc}")
        return 0

    result = anyio.run(run_review, target, config)
    if result is None:
        print("[warn] no ResultMessage received")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORT_DIR / f"review-{stamp}.md"
    report_path.write_text(
        f"# Autopilot review of {target.name}\n\n"
        f"Session: {result.session_id}  \n"
        f"Cost: ${result.total_cost_usd:.6f}  \n"
        f"Turns: {result.num_turns}  \n\n"
        f"{result.result or ''}\n"
    )

    if result.total_cost_usd:
        from anthropic_api_kit.pricing import CostEstimate

        # Record the SDK-reported ACTUAL cost into our own ledger too, so
        # Agent SDK spend and direct Messages API spend share one budget
        # instead of two independent trackers that could each look fine
        # while the combined spend is over cap.
        actual = CostEstimate(
            model=config.routine_model,
            input_tokens=0,
            output_tokens=0,
            input_cost_usd=result.total_cost_usd,
            output_cost_usd=0.0,
        )
        budget.record(actual, model=config.routine_model, request_id=result.session_id)

    print(f"\nWrote {report_path}")
    print(f"Cycle spend now: ${budget.spent_this_cycle():.4f} / ${config.monthly_budget_usd:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
