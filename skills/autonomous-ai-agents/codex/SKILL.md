---
name: codex
description: "Delegate coding to OpenAI Codex CLI (features, PRs)."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring, PTY, Automation]
    related_skills: [claude-code, hermes-agent]
---

# Codex CLI — Hermes Orchestration Guide

Delegate coding tasks to [Codex](https://developers.openai.com/codex) (OpenAI's autonomous coding agent CLI) via the Hermes terminal. Codex can read files, write code, run shell commands, spawn subagents, and manage git workflows autonomously.

## Prerequisites

- **Install:** `npm install -g @openai/codex`
- **Auth:** run `codex login` once (OAuth via ChatGPT/Codex subscription), or set `OPENAI_API_KEY` / `CODEX_API_KEY` for non-interactive runs
- **Check status:** `codex login status`
- **Health check:** `codex doctor` — diagnostic report for installation/config issues (`--json` for machine-readable)
- **Must run inside a git repository** — Codex refuses to run outside one unless `--skip-git-repo-check` is passed to `exec`
- **Use `pty=true`** in terminal calls for interactive mode — Codex's TUI is a full-screen terminal app

For Hermes itself, `model.provider: openai-codex` uses Hermes-managed Codex OAuth from `~/.hermes/auth.json` after `hermes auth add openai-codex`. For the standalone Codex CLI, a valid CLI OAuth session lives under `$CODEX_HOME/auth.json` (`CODEX_HOME` defaults to `~/.codex`); do not treat a missing `OPENAI_API_KEY` alone as proof that Codex auth is missing.

## Two Orchestration Modes

Hermes interacts with Codex in two fundamentally different ways. Choose based on the task.

### Mode 1: `exec` — Non-Interactive (PREFERRED for most tasks)

`codex exec` (alias `codex e`) runs a scripted task and pipes the final plan/result back to stdout, then exits. No PTY needed.

```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work (Codex needs a git repo):
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

**When to use exec mode:**
- One-shot coding tasks (fix a bug, add a feature, refactor)
- CI/CD automation and scripting
- Structured data extraction with `--output-schema`
- Any task where you don't need multi-turn conversation

### Mode 2: Interactive TUI via tmux — Multi-Turn Sessions

Interactive mode gives a full conversational TUI where you can send follow-up prompts, use slash commands, and watch Codex work in real time. **Requires tmux orchestration**, same as any full-screen terminal app.

```
# Start a tmux session
terminal(command="tmux new-session -d -s codex-work -x 140 -y 40")

# Launch Codex inside it
terminal(command="tmux send-keys -t codex-work 'cd /path/to/project && codex' Enter")

# Wait for startup (and the trust dialog on first visit), then send your task
terminal(command="sleep 4 && tmux send-keys -t codex-work Enter")   # accept trust dialog if shown
terminal(command="tmux send-keys -t codex-work 'Refactor the auth module to use JWT tokens' Enter")

# Monitor progress by capturing the pane
terminal(command="sleep 15 && tmux capture-pane -t codex-work -p -S -50")

# Send follow-up tasks
terminal(command="tmux send-keys -t codex-work 'Now add unit tests for the new JWT code' Enter")

# Exit when done
terminal(command="tmux send-keys -t codex-work '/quit' Enter")
```

**When to use interactive mode:**
- Multi-turn iterative work (refactor → review → fix → test cycle)
- Tasks requiring human-in-the-loop decisions (approvals, `/approve`)
- Exploratory coding sessions
- When you need slash commands (`/review`, `/plan`, `/diff`, `/model`)

## Background Mode (Long Tasks)

```
# Start in background with PTY
terminal(command="codex exec 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
# Returns session_id

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

## Approval & Sandbox Model

Codex does not have a single on/off autonomy switch. Two independent axes control it:

| Axis | Flag | Values |
|------|------|--------|
| **Approval policy** — when to pause for a human | `--ask-for-approval, -a` | `untrusted`, `on-request`, `never` |
| **Sandbox policy** — what the shell is allowed to touch | `--sandbox, -s` | `read-only`, `workspace-write`, `danger-full-access` |

Shortcuts:

| Flag | Effect |
|------|--------|
| `--full-auto` | Auto-approves changes; **locks the sandbox to `workspace-write`** even if you also pass `danger-full-access` — deprecated in `exec`, prefer `--sandbox workspace-write` explicitly |
| `--dangerously-bypass-approvals-and-sandbox` (alias `--yolo`) | No sandbox, no approvals — only inside a disposable VM/container |
| `--sandbox danger-full-access` (without `--full-auto`) | Full filesystem access but still asks for approvals unless combined with `-a never` |

**Trust:** the first time Codex runs in a directory it asks to trust it (like Claude Code's workspace trust dialog). Untrusted projects skip project-scoped `.codex/` layers entirely (config, hooks, rules) — only `~/.codex/` (global) applies.

## Hermes Gateway Caveat

When invoking the Codex CLI from a Hermes gateway/service context (for example,
Telegram-driven agent sessions), Codex `workspace-write` sandboxing may fail even
when the same command works in the user's interactive shell. A typical symptom is
bubblewrap/user-namespace errors such as `setting up uid map: Permission denied`
or `loopback: Failed RTM_NEWADDR: Operation not permitted`.

In that context, prefer:

```
codex exec --sandbox danger-full-access -a never "<task>"
```

Use process boundaries as the safety layer instead: explicit `workdir`, clean git
status before launch, narrow task prompts, `git diff` review, targeted tests, and
human/agent confirmation before committing broad changes.

## CLI Subcommands

| Subcommand | Purpose |
|------------|---------|
| `codex` | Launch the interactive TUI |
| `codex exec "prompt"` (`codex e`) | Non-interactive one-shot, exits when done |
| `codex exec resume [SESSION_ID]` | Resume a previous exec session non-interactively |
| `codex resume [id]` | Continue an interactive session by ID, or `--last`/`--all` |
| `codex fork [id]` | Create a new thread from a previous session, keeping the transcript |
| `codex apply` (`codex a`) | Apply the latest diff from a Codex Cloud task to the local repo |
| `codex cloud exec` / `codex cloud list` | Submit/list Codex Cloud background tasks |
| `codex archive` / `codex unarchive` / `codex delete` | Manage saved sessions |
| `codex login` / `codex logout` / `codex login status` | Auth management |
| `codex mcp add / list / get / remove` | Manage MCP servers in `config.toml` |
| `codex mcp-server` | Run Codex itself as an MCP server over stdio |
| `codex sandbox` | Execute a command directly under Codex's sandbox policy (debugging) |
| `codex doctor` | Diagnostic report on installation/config health |
| `codex execpolicy check` | Preview whether a command would be auto-approved |
| `codex plugin` | Install/list/remove plugins |
| `codex app` / `codex app-server` | Desktop app / local app-server for IDE integrations |
| `codex completion` | Generate shell completion scripts |
| `codex update` | Check for and apply CLI updates |

## Exec Mode Deep Dive

### JSON Output
```
terminal(command="codex exec 'Analyze auth.py for security issues' --json --output-last-message /tmp/result.txt", workdir="/project", timeout=120)
```
`--json` / `--experimental-json` streams newline-delimited JSON events. `--output-last-message, -o <path>` writes just the final message to a file — convenient when you only need the end result.

### Structured Output
```
terminal(command="codex exec 'List all functions in src/' --output-schema schema.json", workdir="/project", timeout=90)
```
Validates the final response against a JSON Schema file.

### Ephemeral / CI Runs
```
terminal(command="codex exec --ephemeral --skip-git-repo-check 'Run all tests and report failures'", workdir="/project", timeout=180)
```
`--ephemeral` skips persisting session files. `--skip-git-repo-check` allows running outside a git repo. `--ignore-user-config` skips `config.toml` entirely; `--ignore-rules` skips execpolicy rule files — both useful for hermetic CI runs.

### Resuming an Exec Session
```
terminal(command="codex exec resume --last 'Continue and add connection pooling'", workdir="/project", timeout=120)
```

## Complete CLI Flags Reference

### Global Flags (work on `codex` and `codex exec`)
| Flag | Effect |
|------|--------|
| `--sandbox, -s <mode>` | `read-only` \| `workspace-write` \| `danger-full-access` |
| `--ask-for-approval, -a <mode>` | `untrusted` \| `on-request` \| `never` |
| `--model, -m <name>` | Override configured model |
| `--profile, -p <name>` | Layer an additional config file (`$CODEX_HOME/<name>.config.toml`) |
| `--config, -c <key=value>` | Override a single config value (repeatable) |
| `--cd, -C <path>` | Set working directory |
| `--add-dir <path>` | Grant additional directory write access without escalating the whole sandbox |
| `--image, -i <path[,path...]>` | Attach images to the prompt |
| `--dangerously-bypass-approvals-and-sandbox` (`--yolo`) | Skip all safety checks |
| `--dangerously-bypass-hook-trust` | Run hooks without trust verification |
| `--oss` | Use a local open-source model provider |
| `--search` | Enable live web search for this run |
| `--strict-config` | Error out on unrecognized config fields (catches typos) |
| `PROMPT` | Positional prompt string, or `-` to read from stdin |

### `codex exec`-only flags
| Flag | Effect |
|------|--------|
| `--ephemeral` | Don't persist session files |
| `--json` / `--experimental-json` | Newline-delimited JSON output |
| `--output-last-message, -o <path>` | Write only the final message to a file |
| `--output-schema <path>` | Validate the response against a JSON Schema |
| `--ignore-rules` | Skip execpolicy rule files |
| `--ignore-user-config` | Skip `config.toml` entirely |
| `--skip-git-repo-check` | Allow running outside a git directory |
| `--full-auto` | Deprecated — prefer `--sandbox workspace-write -a on-request` explicitly |

### `codex resume` / `codex fork` flags
| Flag | Effect |
|------|--------|
| `--last` | Skip the picker, use the most recent session |
| `--all` | Include sessions outside the current directory |

## Settings & Configuration

### File Locations (highest to lowest priority within a trusted project)
1. **CLI flags** — override everything
2. **Project-scoped:** `<repo>/.codex/config.toml` — only loaded when the project is marked **trusted**
3. **User:** `$CODEX_HOME/config.toml` (defaults to `~/.codex/config.toml`) — machine-wide

Project-scoped config **cannot** override machine-local provider/auth, host-owned app request metadata, notifications, profile selection, or telemetry routing — those stay global by design.

**Profiles:** named config layers stored as `$CODEX_HOME/<profile-name>.config.toml`, selected via `--profile <name>`.

### Key `config.toml` Sections
```toml
model = "gpt-5.5"
model_reasoning_effort = "high"           # minimal|low|medium|high|xhigh
approval_policy = "on-request"            # untrusted|on-request|never
sandbox_mode = "workspace-write"

[mcp_servers.github]
command = "npx"
args = ["@modelcontextprotocol/server-github"]
startup_timeout_sec = 10

[sandbox_workspace_write]
writable_roots = ["/tmp/scratch"]
network_access = false
```

| Key | Purpose |
|-----|---------|
| `model_instructions_file` | Custom instructions file path, replaces `AGENTS.md` |
| `project_doc_max_bytes` | Max bytes read from `AGENTS.md` |
| `project_doc_fallback_filenames` | Extra filenames to try when `AGENTS.md` is missing |
| `web_search` | `disabled` \| `cached` \| `live` (default `cached`) |
| `features.multi_agent` | Enable agent-spawning tools (default `true`) |
| `features.memories` | Enable the memories feature (default `false`) |
| `history.persistence` | `save-all` \| `none` |
| `shell_environment_policy.inherit` | `all` \| `core` \| `none` — what env vars subprocess shells see |

## AGENTS.md — Project Context File

Codex auto-loads `AGENTS.md` from the project root (same convention Claude Code, Cursor, and others share). Use `/init` inside Codex to generate a scaffold, or write it directly:

```markdown
# Project: My API

## Architecture
- FastAPI backend with SQLAlchemy ORM
- PostgreSQL database, Redis cache

## Key Commands
- `make test` — run full test suite
- `make lint` — ruff + mypy

## Code Standards
- Type hints on all public functions
- No wildcard imports
```

**Be specific** — same principle as `CLAUDE.md`. A repo can carry both files; Codex reads `AGENTS.md`, Claude Code reads `CLAUDE.md`. Keep them in sync manually or point one at the other with a one-line pointer if the project uses both agents (see the `claude-code` skill for the Claude-side equivalent).

## Interactive Session: Slash Commands

### Session & Context
| Command | Purpose |
|---------|---------|
| `/clear` | Reset the visible UI and conversation for a fresh start |
| `/new` | Start a fresh conversation within the same CLI session |
| `/resume` | Continue work from a previous CLI session |
| `/fork` | Clone the current conversation into a new thread |
| `/side` (`/btw`) | Begin an ephemeral side conversation without polluting main context |
| `/compact` | Summarize the visible conversation to free tokens |
| `/status` | Confirm active model, approval policy, writable roots |
| `/usage` | View token usage / rate-limit reset info |
| `/archive` / `/delete` | Remove a session from active list / permanently delete it |
| `/quit` (`/exit`) | Close the CLI |

### Development & Review
| Command | Purpose |
|---------|---------|
| `/review` | Request a working-tree analysis |
| `/diff` | Show git changes including untracked files |
| `/plan` | Propose an execution plan before implementation starts |
| `/goal` | Give Codex a persistent target to track during a larger task |
| `/approve` | Retry a command/action the auto-reviewer denied |
| `/permissions` | Relax or tighten approval requirements mid-session |

### Configuration & Tools
| Command | Purpose |
|---------|---------|
| `/model` | Choose the active model (and reasoning effort) |
| `/personality` | Adjust tone: more concise, explanatory, or collaborative |
| `/mcp` | List configured MCP tools |
| `/hooks` | Inspect, review, and trust lifecycle hooks |
| `/skills` | Select a relevant local skill for the current task |
| `/agent` | Switch active agent thread (multi-agent mode) |
| `/experimental` | Enable optional features such as subagents |
| `/apps` | Attach an app as `$app-slug` before asking Codex to use it |
| `/ide` | Pull editor context into the next prompt |
| `/import` | Migrate Claude Code artifacts into Codex |
| `/init` | Generate an `AGENTS.md` scaffold |
| `/feedback` | Submit diagnostics to the Codex team |

### Custom Prompts (Slash Commands)
Markdown files in `~/.codex/prompts/` (top-level only, user-scoped — **no project-level equivalent**; use skills for repo-shared workflows):

```markdown
---
description: Draft a PR description from the current diff
argument-hint: [BASE=<branch>]
---
Summarize `git diff $BASE...HEAD` as a PR description with a Summary and Test Plan section.
```

Invoke with `/prompts:draftpr BASE=main`. Placeholders: `$1`–`$9` (positional), `$ARGUMENTS` (all args concatenated), `$UPPERCASE_NAME` (named, supplied as `KEY=value`), `$$` (literal `$`).

## Hooks — Automation on Events

Configure in `[hooks]` inside `config.toml`, or a dedicated `hooks.json`:
- `~/.codex/hooks.json` or `[hooks]` in `~/.codex/config.toml` (global)
- `<repo>/.codex/hooks.json` or `[hooks]` in `<repo>/.codex/config.toml` (project, only when trusted)

Higher-precedence layers **add to**, not replace, lower-precedence hooks.

```toml
[[hooks.PreToolUse]]
matcher = "^Bash$"

[[hooks.PreToolUse.hooks]]
type = "command"
command = '/usr/bin/python3 "path/to/script.py"'
timeout = 30
statusMessage = "Checking command"
```

### Hook Event Types
| Event | Fires |
|-------|-------|
| `SessionStart` | On session startup, resume, clear, or compact |
| `SubagentStart` / `SubagentStop` | When a subagent begins / stops |
| `PreToolUse` | Before Bash, `apply_patch`, or MCP tool calls |
| `PostToolUse` | After a tool produces output |
| `PermissionRequest` | Before approval prompts for escalations |
| `PreCompact` / `PostCompact` | Around conversation compaction |
| `UserPromptSubmit` | When the user submits a prompt |
| `Stop` | When a turn completes |

### Blocking an Action
`PreToolUse` — deny a tool call:
```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Destructive command blocked."}}
```
`UserPromptSubmit` / `Stop` — block via exit code `2`, or `{"decision": "block", "reason": "..."}`.

**Trust:** non-managed command hooks must be reviewed and trusted (via `/hooks`) before they run — same trust model as the workspace-trust dialog. Pass `--dangerously-bypass-hook-trust` to skip this in CI (only where the hook source is already controlled). Default hook timeout: 600s, configurable per hook.

## MCP Integration

```
# CLI-managed
terminal(command="codex mcp add github -- npx -y @modelcontextprotocol/server-github", timeout=30)
terminal(command="codex mcp list")
terminal(command="codex mcp remove github")
```

Or edit `config.toml` directly:
```toml
[mcp_servers.postgres]
command = "npx"
args = ["@modelcontextprotocol/server-postgres", "--connection-string", "postgresql://localhost/mydb"]
startup_timeout_sec = 10
tool_timeout_sec = 60

[mcp_servers.remote_api]
url = "https://mcp.example.com/sse"
bearer_token_env_var = "EXAMPLE_MCP_TOKEN"
```

Transport is inferred: `command` → stdio, `url` → streamable HTTP/SSE. Per-server `enabled_tools` / `disabled_tools` allowlist/denylist individual tools; `default_tools_approval_mode` (`auto`/`prompt`/`approve`) controls whether MCP tool calls need human sign-off.

Codex can also **run as an MCP server itself** (`codex mcp-server`, stdio) for downstream tools/IDEs to call into.

## Multi-Agent / Subagents

Enable with `/experimental` (subagents) or `features.multi_agent = true` in config. Switch between threads with `/agent`.

```toml
[agents]
max_threads = 6            # concurrent agent threads
max_depth = 1               # nesting depth
job_max_runtime_seconds = 1800

[agents.reviewer]
description = "Reviews diffs for security issues"
```

## Environment Variables

| Variable | Effect |
|----------|--------|
| `CODEX_HOME` | Root for config, auth, logs, sessions, skills (default `~/.codex`) |
| `CODEX_API_KEY` | API key for a single non-interactive `exec` run |
| `CODEX_ACCESS_TOKEN` | ChatGPT/Codex access token for trusted automation |
| `OPENAI_API_KEY` | Standard API key (interactive login alternative) |
| `CODEX_SQLITE_HOME` | Where SQLite-backed state is stored |
| `CODEX_NON_INTERACTIVE` | `1`/`true`/`yes` — skip installer prompts |
| `CODEX_CA_CERTIFICATE` / `SSL_CERT_FILE` | Custom CA bundle for corporate TLS interception |
| `RUST_LOG` | Rust log filtering/verbosity for CLI and app-server |

## Cost & Performance Tips

1. **Set `model_reasoning_effort`** (`minimal`/`low`/`medium`/`high`/`xhigh`) — low for simple tasks, high for complex multi-step work.
2. **Use `service_tier = "flex"`** in config for cheaper, slower runs when latency doesn't matter.
3. **Prefer `exec` over interactive** for one-shot automation — no TUI overhead, cleaner integration.
4. **`--ignore-user-config`** in CI to get hermetic runs unaffected by a developer's local `config.toml`.
5. **`/compact`** in interactive sessions when context gets large; `model_auto_compact_token_limit` automates the threshold.
6. **`web_search = "cached"`** (the default) avoids paying for live search on every turn — set `"live"` only when freshness matters.
7. **Narrow `--add-dir`** instead of escalating the whole sandbox to `danger-full-access` when Codex just needs one extra directory.

## Pitfalls & Gotchas

1. **`--full-auto` silently locks the sandbox to `workspace-write`** — even if you also pass `--sandbox danger-full-access`, `--full-auto` wins and restricts you back down. Drop `--full-auto` if you actually need full access.
2. **There is no literal `--yolo` flag in some doc snapshots** — it's an alias for `--dangerously-bypass-approvals-and-sandbox`; both work, but scripts should use the explicit long form for clarity.
3. **Untrusted projects skip `.codex/` project-scoped layers entirely** — config, hooks, and rules in `<repo>/.codex/` are silently ignored until the directory is trusted (first-run dialog, same UX as Claude Code's workspace trust).
4. **Custom prompts have no project-level directory** — `~/.codex/prompts/` is user-global only; use Codex **skills** (not covered here) for repo-shared reusable workflows.
5. **`--max-turns`-style loop caps don't exist the same way** — rely on `agents.job_max_runtime_seconds`, `--output-schema` validation, and narrow prompts to bound agentic loops instead.
6. **Git repo required for `exec`** unless `--skip-git-repo-check` is passed — same constraint as before, now with an explicit escape hatch.
7. **PTY required for interactive mode** — Codex's TUI hangs without one; always set `pty=true`.
8. **Hooks require trust just like the workspace itself** — a hook silently added to a repo won't fire until reviewed via `/hooks`, which is a feature, not a bug, but easy to mistake for "hooks aren't working."
9. **`model_instructions_file` overrides `AGENTS.md` entirely** — if a project sets this in `config.toml`, editing `AGENTS.md` won't do anything; check config first if instructions seem to be ignored.

## PR Reviews

Clone to a temp directory for safe review:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex exec '/review'", pty=true)
```

## Parallel Issue Fixing with Worktrees

```
# Create worktrees
terminal(command="git worktree add -b fix/issue-78 /tmp/issue-78 main", workdir="~/project")
terminal(command="git worktree add -b fix/issue-99 /tmp/issue-99 main", workdir="~/project")

# Launch Codex in each
terminal(command="codex exec --sandbox workspace-write -a never 'Fix issue #78: <description>. Commit when done.'", workdir="/tmp/issue-78", background=true, pty=true)
terminal(command="codex exec --sandbox workspace-write -a never 'Fix issue #99: <description>. Commit when done.'", workdir="/tmp/issue-99", background=true, pty=true)

# Monitor
process(action="list")

# After completion, push and create PRs
terminal(command="cd /tmp/issue-78 && git push -u origin fix/issue-78")
terminal(command="gh pr create --repo user/repo --head fix/issue-78 --title 'fix: ...' --body '...'")

# Cleanup
terminal(command="git worktree remove /tmp/issue-78", workdir="~/project")
```

## Batch PR Reviews

```
# Fetch all PR refs
terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'", workdir="~/project")

# Review multiple PRs in parallel
terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)

# Post results
terminal(command="gh pr comment 86 --body '<review>'", workdir="~/project")
```

## Rules for Hermes Agents

1. **Prefer `exec` for single tasks** — cleaner, no dialog handling, structured output via `--json`/`--output-schema`.
2. **Use tmux for multi-turn interactive work** — the only reliable way to orchestrate the TUI.
3. **Always set `workdir`** — keep Codex focused on the right project directory.
4. **Be explicit about `--sandbox` and `-a`** — don't rely on `--full-auto`'s implicit lock; state the sandbox and approval policy you actually want.
5. **Background for long tasks** — use `background=true` and monitor with the `process` tool.
6. **Don't interfere** — monitor with `poll`/`log`, be patient with long-running tasks.
7. **Parallel is fine** — run multiple Codex processes at once for batch work, each with its own worktree.
8. **Report results to user** — after completion, summarize what Codex did and what changed.
9. **Treat hooks and `.codex/` config as trust-gated** — a project's own hooks/config won't apply until trusted; don't assume a repo's `.codex/config.toml` is in effect without checking.
