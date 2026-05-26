# Contributing to ae-agentic-skilling

Thanks for considering a contribution. This repo collects Claude Code skills that solve real, reusable problems. The bar is "does this help more than one person."

## Quick start

1. **Fork** this repo on GitHub.
2. **Clone** your fork locally.
3. **Branch** off `main` with a descriptive name (e.g., `feat/screenshot-auto-crop`).
4. **Add your skill** under `skills/<your-skill-name>/` (see structure below).
5. **Push** and open a PR against `main` of this repo.
6. The **PR review workflow** (Claude-powered) runs automatically and posts findings as a comment. Address its feedback or explain why it's wrong.
7. Once approved, a maintainer squashes and merges.

## Skill folder structure

Every skill must include at minimum:

```
skills/<skill-name>/
├── SKILL.md              # Required. Machine-readable trigger metadata (YAML frontmatter) + agent-facing instructions.
├── README.md             # Required. Human-readable: what it does, install, usage example.
├── <scripts...>          # Whatever the skill needs (Python, PowerShell, JS, etc.)
└── requirements.txt      # Required if the skill has Python deps. Pin versions.
```

### `SKILL.md` format

```markdown
---
name: skill-name-in-kebab-case
description: One-paragraph description that helps Claude decide when to invoke this skill. Include trigger phrases like "when the user says X" or "if user hands over a Y file."
---

# Skill Name

Agent-facing instructions: workflow, gotchas, dependencies, when to use, when NOT to use.
```

### `README.md` format

User-facing. Cover:

- **What it does** — one sentence.
- **Install** — external dependencies (e.g., ffmpeg), `pip install -r requirements.txt`.
- **Usage** — a concrete example invocation.
- **Limitations** — platforms tested, known issues.

## Quality rules (enforced by [`pr-review.yml`](.github/workflows/pr-review.yml))

The same rules live in [`CLAUDE.md`](CLAUDE.md), which is the source of truth. Highlights:

- **No hardcoded local paths.** Use environment variables or `shutil.which()` for external binaries.
- **No secrets or tokens in code.** Anything sensitive comes from env vars at runtime.
- **Cross-platform if possible.** If your skill is Windows-only or Mac-only, say so in the README — don't make it look universal when it isn't.
- **Doc-staleness**: if you change a skill's scripts, update its `README.md` and `SKILL.md` in the same PR. The review workflow flags PRs that update scripts without touching docs.
- **Workflow files**: must have `timeout-minutes`, an explicit `permissions:` block, `set -euo pipefail` in shell, and `--max-time` on `curl`.
- **Conventional-ish commit subjects**: `feat:`, `fix:`, `docs:`, `chore:` prefixes are nice but not strictly required.

## Branch protection

`main` is protected:

- All changes go through a PR.
- The PR-review workflow must run (its output is advisory, not blocking — but the workflow itself must complete).
- Direct pushes to `main` are blocked.
- Force-pushes are blocked.

## Security note for fork PRs

The PR-review workflow runs on `pull_request` events, which means **PRs from forks do not have access to repository secrets** — including `CLAUDE_CODE_OAUTH_TOKEN`. This is intentional: it prevents a malicious PR from exfiltrating the token.

The practical effect: **PRs from forks will not get auto-review** until a maintainer pushes the branch into the main repo and runs the workflow manually. Maintainers can do this via `gh pr checkout <PR#>` followed by `git push origin <branch>:<branch>` into a maintainer-controlled branch.

PRs from collaborators (push access to the main repo) get auto-review automatically.

## Reporting bugs / requesting skills

Use the issue templates under `.github/ISSUE_TEMPLATE/`. Include reproduction steps for bugs, use cases for feature requests.

## License

By contributing, you agree your contributions are licensed under [MIT](LICENSE).
