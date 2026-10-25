#!/usr/bin/env python3
"""Poll approved Ads-Wise development tasks and open reviewable GitHub pull requests."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path


MCP_URL = os.getenv("ADS_WISE_MCP_URL", "https://ads-wise.com/mcp/developer")
REPOSITORY = os.getenv("ADS_WISE_REPOSITORY", "ahmedabuseif1997/ads-wise")
POLL_SECONDS = max(20, int(os.getenv("ADS_WISE_RUNNER_POLL_SECONDS", "45")))
RUNNER_NAME = f"{socket.gethostname()}-local"
NOT_BEFORE = os.getenv("ADS_WISE_RUNNER_NOT_BEFORE", "").strip()


def run(command: list[str], *, cwd: Path | None = None, stdin: str | None = None,
        timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, input=stdin, text=True, capture_output=True,
                          timeout=timeout, check=True)


def token() -> str:
    configured = os.getenv("ADS_WISE_MCP_TOKEN", "").strip()
    if configured:
        return configured
    return run(["/usr/bin/security", "find-generic-password", "-s", "ads-wise-mcp-token", "-w"],
               timeout=15).stdout.strip()


def mcp(tool: str, arguments: dict) -> object:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": arguments}}).encode()
    request = urllib.request.Request(MCP_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(payload["error"].get("message", "MCP request failed"))
    content = payload["result"]["content"][0]["text"]
    return json.loads(content)


def cli_ready(agent: str) -> bool:
    try:
        if agent == "codex":
            result = run(["codex", "login", "status"], timeout=20)
            return "Logged in" in (result.stdout + result.stderr)
        status = json.loads(run(["claude", "auth", "status"], timeout=20).stdout)
        return bool(status.get("loggedIn"))
    except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError):
        return False


def report_heartbeats() -> dict[str, bool]:
    readiness = {agent: cli_ready(agent) for agent in ("codex", "claude")}
    for agent, ready in readiness.items():
        mcp("report_runner_status", {"agent": agent, "runner_name": RUNNER_NAME,
                                     "status": "ready" if ready else "unavailable"})
    return readiness


def agent_prompt(task: dict) -> str:
    return f"""Implement this approved Ads-Wise task: {task['instructions']}

Safety and delivery requirements:
- Work only inside this repository and preserve tenant isolation.
- Do not read, print, create, or change secrets or .env files.
- Do not deploy, merge, or write directly to production.
- Make the smallest complete change and run targeted checks for touched code.
- Leave the working tree with the implementation ready for review; do not commit or push.
"""


def execute_agent(agent: str, task: dict, checkout: Path) -> None:
    prompt = agent_prompt(task)
    if agent == "codex":
        run(["codex", "exec", "--approve-for-me", "--sandbox", "workspace-write",
             "--ephemeral", "--cd", str(checkout), "-"], cwd=checkout, stdin=prompt)
    else:
        run(["claude", "--print", "--permission-mode", "acceptEdits",
             "--no-session-persistence", prompt], cwd=checkout)


def forbidden_changes(checkout: Path) -> list[str]:
    changed = run(["git", "status", "--porcelain"], cwd=checkout, timeout=30).stdout.splitlines()
    paths = [row[3:] for row in changed if len(row) > 3]
    forbidden = {".env", ".env.local", ".env.production", "credentials.json"}
    return [path for path in paths if Path(path).name in forbidden or path.startswith(".git/")]


def process_task(agent: str, task: dict) -> None:
    task_id = task["id"]
    branch = f"agent/{agent}/{task_id}"
    mcp("update_development_task", {"id": task_id, "status": "in_progress",
                                    "branch_name": branch})
    temp_root = Path(tempfile.mkdtemp(prefix=f"ads-wise-{agent}-"))
    checkout = temp_root / "repo"
    try:
        run(["gh", "repo", "clone", REPOSITORY, str(checkout), "--", "--depth=1"], timeout=180)
        run(["git", "checkout", "-b", branch], cwd=checkout, timeout=30)
        run(["git", "config", "user.name", f"Ads-Wise {agent.title()} Runner"], cwd=checkout)
        run(["git", "config", "user.email", "info@ads-wise.com"], cwd=checkout)
        execute_agent(agent, task, checkout)
        if forbidden_changes(checkout):
            raise RuntimeError("Runner blocked a change to a protected credential file")
        if not run(["git", "status", "--porcelain"], cwd=checkout, timeout=30).stdout.strip():
            raise RuntimeError("Agent completed without producing a code change")
        run(["git", "add", "-A"], cwd=checkout)
        run(["git", "commit", "-m", f"Agent task {task_id}"], cwd=checkout)
        run(["git", "push", "-u", "origin", branch], cwd=checkout, timeout=180)
        title = task["instructions"].strip().splitlines()[0][:72]
        result = run(["gh", "pr", "create", "--repo", REPOSITORY, "--base", "main",
                      "--head", branch, "--title", title,
                      "--body", f"Ads-Wise {agent.title()} runner task `{task_id}`.\n\nOwner approval is required before merge."],
                     cwd=checkout, timeout=120)
        pr_url = result.stdout.strip().splitlines()[-1]
        mcp("update_development_task", {"id": task_id, "status": "needs_approval",
                                        "branch_name": branch, "pull_request_url": pr_url})
    except Exception:
        mcp("update_development_task", {"id": task_id, "status": "failed",
                                        "branch_name": branch})
        raise
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def cycle() -> None:
    readiness = report_heartbeats()
    for agent, ready in readiness.items():
        if not ready:
            continue
        tasks = mcp("list_development_tasks", {"agent": agent})
        for task in tasks:
            created_at = datetime.fromisoformat(task["created_at"])
            cutoff = datetime.fromisoformat(NOT_BEFORE.replace("Z", "+00:00")) if NOT_BEFORE else None
            if task.get("status") == "awaiting_runner" and (not cutoff or created_at >= cutoff):
                process_task(agent, task)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        try:
            cycle()
        except Exception as exc:
            print(f"developer runner: {exc}", flush=True)
        if args.once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
