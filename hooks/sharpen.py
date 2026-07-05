#!/usr/bin/env python3
"""prompt-sharpener: UserPromptSubmit hook that blocks vague prompts."""

import json
import re
import sys

MAX_LEN = 120
MAX_WORDS = 20

VAGUE = re.compile(
    r"^(?:please\s+|pls\s+|can\s+you\s+|could\s+you\s+)?(?:just\s+)?"
    r"(?P<verb>fix|debug|repair|clean\s*up|tidy(?:\s+up)?|improve|"
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


def main():
    data = json.load(sys.stdin)
    prompt = (data.get("prompt") or "").strip()

    if not prompt or len(prompt) > MAX_LEN or len(prompt.split()) > MAX_WORDS:
        return

    if CHITCHAT.match(prompt):
        return

    if any(pattern.search(prompt) for pattern in SPECIFIC):
        return

    if not VAGUE.match(prompt):
        return

    print(json.dumps({
        "decision": "block",
        "reason": "prompt-sharpener: that prompt looks broad. Add a file, "
                  "an error message, or a specific detail, then resend.",
    }))


if __name__ == "__main__":
    main()
