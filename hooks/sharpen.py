#!/usr/bin/env python3
"""prompt-sharpener: UserPromptSubmit hook that blocks vague prompts."""

import hashlib
import json
import os
import re
import sys
import tempfile

MAX_LEN = 120
MAX_WORDS = 20

VAGUE = re.compile(
    r"^(?:please\s+|pls\s+|can\s+you\s+|could\s+you\s+)?(?:just\s+)?"
    r"(?P<verb>fix|debug|repair|clean(?:\s*up)?|tidy(?:\s+up)?|improve|"
    r"optimi[sz]e|refactor|polish|speed\s+up|make)\b[\s,:]*(?P<rest>.*)$",
    re.IGNORECASE,
)

# Any of these means the user already gave Claude something concrete to
# work with — stay silent.
SPECIFIC = [
    re.compile(r"`"),                                   # inline code
    re.compile(                                         # file names
        r"\b[\w-]+\.(?:tsx?|jsx?|mjs|cjs|py|css|scss|less|html?|json|md|"
        r"ya?ml|toml|sql|go|rs|rb|php|java|sh|zsh|swift|kt|vue|svelte|"
        r"c|h|cpp|hpp|cs|env|txt|lock|cfg|ini)\b",
        re.IGNORECASE,
    ),
    re.compile(r"/\w"),                                 # paths and routes
    re.compile(r"\bline\s+\d+\b|:\d+", re.IGNORECASE),  # line references
    re.compile(r"[A-Z]\w*(?:Error|Exception)\b"),       # named errors
    re.compile(r"\?"),                                  # questions
    re.compile(r"\n"),                                  # multi-line = structured
]

# Conversational replies mid-session — never nag on these.
CHITCHAT = re.compile(
    r"^(?:y|yes|yeah|yep|no|nope|ok(?:ay)?|k|sure|go(?:\s+ahead)?|do\s+it|"
    r"proceed|continue|carry\s+on|keep\s+going|try\s+again|retry|thanks|"
    r"thank\s+you|ty|lgtm|sounds\s+good|option\s+\d+|\d+)[\s.!]*$",
    re.IGNORECASE,
)

# "make" is only vague as "make it/this/everything <goal>" ("make it
# production ready"), not as a creation request ("make a login page").
MAKE_VAGUE = re.compile(r"^(?:it|this|everything)\b", re.IGNORECASE)

FILLER_WORDS = {"the", "my", "our", "this", "that", "it", "up", "all", "some"}
GENERIC_TARGETS = {"", "code", "codebase", "everything", "things", "stuff",
                   "app", "project", "repo", "site", "website"}


def extract_target(rest):
    """Pull the object out of e.g. 'the navbar' -> 'navbar'."""
    words = rest.strip().rstrip(".!,").split()
    while words and words[0].lower() in FILLER_WORDS:
        words.pop(0)
    target = " ".join(words)
    return None if target.lower() in GENERIC_TARGETS else target


BUG_VERBS = {"fix", "debug", "repair"}


def valve_path(session_id):
    return os.path.join(
        tempfile.gettempdir(), "prompt-sharpener-%s.last" % session_id
    )


def digest(prompt):
    normalized = " ".join(prompt.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_suggestion(verb, rest):
    target = extract_target(rest)

    if verb == "make":
        goal = target or "[the goal you have in mind]"
        return (
            "Audit the code we're working on against this goal: %s. "
            "List what concretely falls short — specific files and issues — "
            "before changing anything. Then fix only those items, no broad "
            "rewrites. Run the relevant tests after." % goal
        )

    if verb in BUG_VERBS:
        subject = ("The " + target) if target else "[the thing that's broken]"
        area = ("the " + target) if target else "that area"
        return (
            "%s is misbehaving: [what you see vs. what you expected, and "
            "where it happens]. First locate the code responsible and state "
            "the root cause — don't edit anything until you've explained it. "
            "Keep the fix scoped to the files directly involved, and if a "
            "test covers %s, run it before and after." % (subject, area)
        )

    scope = ("the " + target) if target else "[the code you mean]"
    return (
        "Review %s and list the specific issues you find — [what I care "
        "about: naming, dead code, duplication, error handling?]. Fix only "
        "those issues, no broad rewrites, and limit changes to the files "
        "that implement %s. If tests cover that area, run them after."
        % (scope, scope)
    )


def main():
    data = json.load(sys.stdin)
    prompt = (data.get("prompt") or "").strip()
    session_id = re.sub(r"[^\w-]", "", data.get("session_id") or "global")

    if not prompt or len(prompt) > MAX_LEN or len(prompt.split()) > MAX_WORDS:
        return

    if CHITCHAT.match(prompt):
        return

    if any(pattern.search(prompt) for pattern in SPECIFIC):
        return

    match = VAGUE.match(prompt)
    if not match:
        return
    verb = re.sub(r"\s+", " ", match.group("verb").lower())
    rest = match.group("rest")
    if verb == "make" and not MAKE_VAGUE.match(rest):
        return

    # Safety valve: identical resend of the last blocked prompt goes through.
    state = valve_path(session_id)
    fingerprint = digest(prompt)
    try:
        with open(state) as f:
            if f.read().strip() == fingerprint:
                os.remove(state)
                return
    except OSError:
        pass

    reason = (
        "prompt-sharpener: that prompt is broad enough that Claude may guess "
        "at the scope. Sharper version — edit the [brackets], then send:\n\n"
        "%s\n\n"
        "To send your original as-is, submit the exact same prompt again."
        % build_suggestion(verb, rest)
    )
    with open(state, "w") as f:
        f.write(fingerprint)
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
