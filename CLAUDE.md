# ae-agentic-skilling Quality Rules

Source of truth for PR reviews in this repository. The `pr-review.yml` workflow reads this file and uses it to judge every PR.

## Skill structure

1. Every skill must live in `skills/<kebab-case-name>/`
2. Every skill must include both `SKILL.md` (agent-facing) and `README.md` (user-facing)
3. `SKILL.md` must start with YAML frontmatter containing `name:` and `description:` fields
4. Skills with Python dependencies must include a `requirements.txt` with **pinned versions** (e.g., `faster-whisper==1.2.1`, not `faster-whisper>=1.0`)
5. Skills with external CLI dependencies (ffmpeg, etc.) must document them in the skill's README

## Doc-staleness rule (important)

If a PR modifies a skill's scripts, it must also update the skill's `README.md` and/or `SKILL.md` in the same PR. PRs that change behavior without updating docs are flagged. The exception: pure refactors that don't change observable behavior (rename a variable, restructure code without changing what it does) can pass without doc updates if the PR description clearly states "no behavior change."

## Portability

1. **No hardcoded absolute paths** in published skills. Use `shutil.which()`, env vars, or platform-aware lookups.
2. **No references to a specific user's directory** (`C:\Users\<name>\...` or `/home/<name>/...`)
3. **Cross-platform when possible.** If a skill is platform-specific, the README must say so prominently.
4. **No OneDrive / Dropbox / iCloud absolute paths.** Those are personal storage locations.

## Workflow standards (`.github/workflows/*.yml`)

1. Every job must have `timeout-minutes` set
2. Every workflow must have an explicit top-level `permissions:` block
3. Shell scripts in `run:` blocks must use `set -euo pipefail` (or at minimum `set -e`)
4. Polling loops must have a max iteration cap
5. All `curl` calls must include `--max-time` on the same line as the command
6. Cron expressions must include a comment explaining the schedule in local time

## Secrets & security

1. No hardcoded secrets, tokens, API keys, or passwords
2. All sensitive values must come from `${{ secrets.* }}` in workflows, or environment variables at runtime in scripts
3. Never log secret values
4. Workflows that need secrets must run on `pull_request`, not `pull_request_target`, unless there's a documented reason — `pull_request_target` exposes secrets to fork PRs and is a security footgun

## AI model access

If a skill or workflow needs to call an LLM:

1. **Prefer Claude CLI via OAuth** (`claude -p --no-session-persistence --max-turns N --output-format text`) using the `CLAUDE_CODE_OAUTH_TOKEN` secret. This uses the contributor's own Claude Max subscription at zero per-token cost.
2. **Only use the Anthropic SDK** (`@anthropic-ai/sdk` or `anthropic`) when programmatic tool use with multi-turn dispatch is genuinely required.
3. **Don't call the Anthropic API directly via raw HTTP** for tasks the CLI handles fine.

## Python script standards

1. Use `argparse` for CLI args (not manual `sys.argv` parsing) so `--help` works
2. Print errors to `stderr`, not `stdout`
3. Exit with non-zero on failure
4. If the script needs an external binary, look for it with `shutil.which()` first, then check a `<TOOL>` env var, then error with a clear "install X and ensure it's on PATH" message
5. No `print()` calls for debugging that ship to main — use a real logger or remove before merging

## PowerShell script standards (for Windows-targeted skills)

1. Use `.ps1` files for any non-trivial PowerShell — inline `powershell -Command "..."` mangles `$_`, `$env:`, and `$(...)` when called from bash
2. Quote all paths
3. Use `-ErrorAction Stop` on critical operations

## General

1. Prefer editing existing files over creating new ones
2. Keep shell scripts portable (no bash-specific features without `#!/bin/bash`)
3. Error messages must be actionable (include what failed and what to do about it)
4. README examples must be runnable as-written (no `<your-path-here>` placeholders without a clear example value)
