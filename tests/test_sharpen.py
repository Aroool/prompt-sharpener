#!/usr/bin/env python3
"""Regression harness for hooks/sharpen.py — feeds hook-style JSON on stdin,
checks that the right prompts block and the right prompts pass silently."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
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


def run(prompt, session_id, cwd="/tmp"):
    payload = json.dumps({
        "session_id": session_id,
        "prompt": prompt,
        "hook_event_name": "UserPromptSubmit",
        "cwd": cwd,
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


def sid():
    return "test-" + uuid.uuid4().hex[:8]


def check_repo_aware(failures):
    """Repo-aware rewrites: real file candidates and real test commands."""
    # Node fixture: Navbar.tsx should be named, npm test should be suggested.
    node = tempfile.mkdtemp(prefix="sharpener-node-")
    try:
        subprocess.run(["git", "init", "-q"], cwd=node, check=True)
        os.makedirs(os.path.join(node, "src", "components"))
        for name in ("Navbar.tsx", "Footer.tsx"):
            with open(os.path.join(node, "src", "components", name), "w") as f:
                f.write("export {}\n")
        with open(os.path.join(node, "package.json"), "w") as f:
            json.dump({"scripts": {"test": "vitest run"}}, f)
        reason = run("fix the navbar", sid(), cwd=node) or ""
        if "src/components/Navbar.tsx" not in reason:
            failures.append("repo-aware: should name Navbar.tsx")
        if "Footer.tsx" in reason:
            failures.append("repo-aware: Footer.tsx is not a match")
        if "`npm test`" not in reason:
            failures.append("repo-aware: should suggest npm test")
    finally:
        shutil.rmtree(node, ignore_errors=True)

    # Python fixture: pytest detected, matching module named.
    py = tempfile.mkdtemp(prefix="sharpener-py-")
    try:
        subprocess.run(["git", "init", "-q"], cwd=py, check=True)
        open(os.path.join(py, "pytest.ini"), "w").close()
        with open(os.path.join(py, "auth.py"), "w") as f:
            f.write("pass\n")
        reason = run("refactor the auth code", sid(), cwd=py) or ""
        if "auth.py" not in reason:
            failures.append("repo-aware: should name auth.py")
        if "`pytest`" not in reason:
            failures.append("repo-aware: should suggest pytest")
    finally:
        shutil.rmtree(py, ignore_errors=True)

    # Outside a git repo: fall back to the generic wording, never crash.
    bare = tempfile.mkdtemp(prefix="sharpener-bare-")
    try:
        reason = run("fix the navbar", sid(), cwd=bare) or ""
        if "locate the code responsible" not in reason:
            failures.append("repo-aware: non-git cwd should use generic wording")
    finally:
        shutil.rmtree(bare, ignore_errors=True)


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

    check_repo_aware(failures)

    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("All %d cases passed." % (len(BLOCK) + len(PASS) + 12))


if __name__ == "__main__":
    main()
