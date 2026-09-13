# Setup and troubleshooting

[Back to Claude + Astra Router](../README.md)

## Local prerequisites

This initial recipe uses local Claude Code and Codex CLI on the same computer, with Python 3 and a Git project. It has been developed on macOS. Follow the official installation instructions for your platform: [Claude Code](https://code.claude.com/docs/en/quickstart), [Codex CLI](https://learn.chatgpt.com/docs/cli).

From a terminal in the project, these commands inspect availability:

```bash
python3 --version
claude --version
codex --version
codex login status
```

If needed, run `codex login` yourself and complete the sign-in flow. Never put a credential into a task brief. Start Claude Code and complete its own login separately. Model access is checked by a real worker call; no subscription tier is assumed to guarantee Astra.

A ZIP download needs a local Git repository before Codex will run. In that new, isolated folder, `git init` is sufficient. This does not create or publish a GitHub repository. Do not use a broad existing folder as the trial project.

Copy the template to root `CLAUDE.md` and start a fresh Claude session there. For an existing project, merge deliberately; preserve its other rules. The script can also be run by hand, but that alone is not a test of Claude directing it.

## Where the information goes

Claude reads the inputs needed to plan and review. The task brief and material Astra reads are also processed through Codex. The tools do not automatically share chat history or connectors. Use only material allowed in both environments.

Run folders contain the brief, worker result, events and state needed to identify the exact session. Those files may contain task information; treat the whole run folder as private. `work/` is ignored by Git, but an ignore rule is not a data-handling policy.

## Permissions

Start in read-only mode for reports and analysis. The result file is saved by the runner; Astra does not need to edit source files just to return text. Select workspace-write only for an authorised task that needs project edits, and include the exact file scope in the brief. The selected sandbox applies again when revising.

Claude's command permission prompts and Codex's existing rules still apply. If a nested non-interactive worker cannot obtain required permission, surface the failure. Do not remove the sandbox or disable rules to force a pass.

## Common failures

| Symptom | Response |
|---|---|
| `codex` or Python is not found | Install the missing prerequisite through its official instructions, then reopen the terminal or Claude session |
| Codex is not signed in | Complete `codex login`; do not copy auth files into the project |
| Astra is not available | Check the account's model access; stop instead of silently substituting another model |
| The folder is not a Git repository | Initialise Git in the isolated trial folder or use a clone |
| The run directory already exists | Use a new task directory; do not overwrite the previous run |
| A previous attempt failed | Inspect its error and actual file changes before starting another task; failed processes may have made partial changes |
| Revision is refused | Check the saved state and revision limit; start a new, explicitly scoped task only after the user resolves the remaining issue |
| Claude says it delegated, but no result exists | Require the real command result and artifact paths; do not accept a narrated handoff |
| A worker cannot read a source Claude can access | Supply a permitted extract or solve access; a second model does not inherit Claude's connectors |

## Check the implementation

The script requires only Python's standard library. Its subprocess tests do not require model access:

```bash
python3 -m unittest discover -s tests -v
```

For a live test, use the README's fictional task and inspect both the command record and the returned content. A successful dispatch only shows that the connection worked. Review/revision quality must be assessed separately. See the dated [validation record](validation.md).
