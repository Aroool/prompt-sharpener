# prompt-sharpener

Catches vague prompts ("fix the navbar", "make it production ready", "clean
this up") **before** Claude runs, and shows you a sharper version to send
instead — so Claude gets it right the first time instead of burning tokens
guessing wrong.

## How it works

A `UserPromptSubmit` hook checks each prompt with fast, local heuristics
(no API calls). If the prompt is clearly vague — a broad imperative verb with
no file, path, code reference, error name, or detail — it blocks the prompt
(nothing is sent, zero tokens used) and prints a sharper rewrite that:

- describes what to investigate,
- asks Claude to find the root cause before editing,
- limits the scope of changes,
- and asks to run the relevant test if one exists.

You copy it, edit the `[brackets]`, and send. Your prompt is **never**
rewritten silently — you always make the final send.

### Repo-aware rewrites (v0.2)

The suggestion is grounded in your actual project, not just a template:

- **Real files**: "fix the navbar" becomes "Likely code:
  `src/components/Navbar.tsx` — confirm that's the right place…" by matching
  the target noun against `git ls-files` (fast, respects `.gitignore`, only
  runs when a prompt is actually blocked).
- **Real test command**: it detects `npm test` / `pnpm test` / `yarn test` /
  `bun test` (from `package.json` + lockfile), `pytest`, `cargo test`, or
  `go test ./...` and names that command instead of "if a test exists".

Outside a git repo, or when nothing matches, it falls back to the generic
wording. Still no API calls, no config, no state.

**Safety valve:** if it flags a prompt you meant literally, just submit the
exact same prompt again and it goes straight through.

If the prompt is already specific, the hook stays completely silent.

## Install

Requires `python3` on PATH (stdlib only, no packages).

```bash
claude --plugin-dir /path/to/prompt-sharpener
```

Or install via a marketplace / copy into your plugins setup. No configuration.

## Try it

Inside the session, submit:

```
fix the navbar
```

It gets blocked with a sharper suggestion. Submit it again unchanged to force
it through, or send the suggested version instead.
