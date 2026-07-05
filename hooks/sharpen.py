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


def main():
    data = json.load(sys.stdin)
    prompt = (data.get("prompt") or "").strip()

    if not prompt or len(prompt) > MAX_LEN or len(prompt.split()) > MAX_WORDS:
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
