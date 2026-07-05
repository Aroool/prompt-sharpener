#!/usr/bin/env python3
"""Regression harness for hooks/sharpen.py — feeds hook-style JSON on stdin,
checks that the right prompts block and the right prompts pass silently."""
import json
import os
import subprocess
import sys
import uuid

SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "hooks", "sharpen.py"
)

BLOCK = [
    "fix the navbar",
    "clean this up",
    "make it production ready",
    "refactor the auth code",
    "please just fix the login flow",
    "optimize it",
    "improve the dashboard",
    "polish the settings page",
    "debug the signup form",
    "speed up the build",
]

PASS = [
    "Fix the dropdown in src/components/Nav.tsx - it closes on hover instead of click",
    "yes",
    "continue",
    "go ahead",
    "try again",
    "why is the navbar broken?",
    "fix the TypeError in the login handler",
    "make a login page",
    "make me a sandwich",
    "fix the navbar in Header.tsx",
    "optimize `getUsers`",
    "fix the bug on line 42",
    "fix the /about route so the hero image loads",
    "clean up the imports in utils.py",
    "The navbar overlaps the sidebar on mobile widths below 400px. Find the CSS responsible and fix only that rule.",
    "thanks",
    "lgtm",
    "2",
    "option 1",
    "rename getUser to fetchUser everywhere",
    "add a dark mode toggle to the settings page header, persisted in localStorage",
]


def run(prompt, session_id):
    payload = json.dumps({
        "session_id": session_id,
        "prompt": prompt,
        "hook_event_name": "UserPromptSubmit",
        "cwd": "/tmp",
    })
    result = subprocess.run(
        ["python3", SCRIPT], input=payload, capture_output=True, text=True
    )
    assert result.returncode == 0, "nonzero exit for %r: %s" % (prompt, result.stderr)
    out = result.stdout.strip()
    if not out:
        return None
    parsed = json.loads(out)
    assert parsed.get("decision") == "block", "unexpected output for %r: %s" % (prompt, out)
    return parsed["reason"]


def main():
    failures = []

    for p in BLOCK:
        sid = "test-" + uuid.uuid4().hex[:8]
        if run(p, sid) is None:
            failures.append("SHOULD BLOCK but passed: %r" % p)

    for p in PASS:
        sid = "test-" + uuid.uuid4().hex[:8]
        if run(p, sid) is not None:
            failures.append("SHOULD PASS but blocked: %r" % p)

    # Safety valve: identical resend in the same session passes through once.
    sid = "test-valve-" + uuid.uuid4().hex[:8]
    first = run("fix the navbar", sid)
    second = run("fix the navbar", sid)
    third = run("fix the navbar", sid)
    if first is None:
        failures.append("valve: first submit should block")
    if second is not None:
        failures.append("valve: identical resend should pass through")
    if third is None:
        failures.append("valve: after valve consumed, should block again")

    # Valve must be per-session.
    run("fix the navbar", "test-valve-a-" + uuid.uuid4().hex[:8])
    if run("fix the navbar", "test-valve-b-" + uuid.uuid4().hex[:8]) is None:
        failures.append("valve: leaked across sessions")

    # Malformed input must not crash or block.
    r = subprocess.run(["python3", SCRIPT], input="not json", capture_output=True, text=True)
    if r.returncode != 0 or r.stdout.strip():
        failures.append("malformed input should exit 0 silently")

    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("All %d cases passed." % (len(BLOCK) + len(PASS) + 5))


if __name__ == "__main__":
    main()
