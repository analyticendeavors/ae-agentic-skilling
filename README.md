# AE Agentic Skilling

Reusable [Claude Code](https://docs.claude.com/en/docs/claude-code) skills, started by [Analytic Endeavors](https://analyticendeavors.com), open to community contribution.

A **skill** is a small bundle of instructions + scripts that Claude Code can invoke on demand. Skills live in your `~/.claude/skills/` folder and are triggered by natural-language phrases. This repo collects skills that solve real, repeatable problems.

## Skills

| Skill | What it does |
|---|---|
| [camtasia-auto-edit](skills/camtasia-auto-edit/) | Detect filler words (um/uh), long silences, and re-take attempts in a Camtasia recording. Drop visible Camtasia markers on the timeline so you can scrub-and-cut. Windows-tested. |

More coming. PRs welcome (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Installing a skill

Claude Code automatically discovers skills in `~/.claude/skills/` on every machine.

1. Clone this repo somewhere convenient:
   ```bash
   git clone https://github.com/analyticendeavors/ae-agentic-skilling.git
   ```
2. Symlink the skill folder into your Claude Code skills directory. On Windows (PowerShell as admin):
   ```powershell
   New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\camtasia-auto-edit" -Target "C:\path\to\ae-agentic-skilling\skills\camtasia-auto-edit"
   ```
   On macOS / Linux:
   ```bash
   ln -s "$(pwd)/skills/camtasia-auto-edit" "$HOME/.claude/skills/camtasia-auto-edit"
   ```
3. Open a Claude Code session. The skill is now available — invoke it by name or by the trigger phrases listed in the skill's own README.

Per-skill setup (Python deps, external CLIs like ffmpeg) lives in each skill's `README.md`.

## Secrets

`ANTHROPIC_API_KEY` is a **repo-level** secret and is what the workflows here use (`pr-review.yml`, `model-currency-audit.yml`).

This repo is **public**, so it cannot read the org-level `CLAUDE_CODE_OAUTH_TOKEN`: that secret has `visibility: private`, meaning private and internal repositories only. Workflows here are therefore billed per token rather than running free on a Max subscription.

Do NOT add `CLAUDE_CODE_OAUTH_TOKEN` as a repo-level secret here. A repo-level copy shadows the org-level one and silently survives org-level rotation, so a stale token can sit unnoticed indefinitely. Rotate the org secret at github.com/organizations/analyticendeavors/settings/secrets/actions; rotate this repo's API key in the Anthropic Console.

## What's NOT here

- Anything business-specific to AE (lead enrichment, CRM integrations, internal tooling). Those live in private repos.
- Skills that only work on one machine. Everything here should run on any reasonably-configured developer setup.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). TL;DR: fork, add a skill folder under `skills/`, include a `SKILL.md` + per-skill `README.md`, target `main` with your PR.

## License

[MIT](LICENSE). Use it, fork it, build on it.
