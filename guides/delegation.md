# Claude directs Astra through Codex

Start at the [README](../README.md), use the [Claude instruction template](../templates/CLAUDE.md), and follow [setup and troubleshooting](setup.md).

Claude Code is the lead. The local runner dispatches work to `gpt-6-astra` through Codex and targets that exact session when Claude requests a revision. See [validation](validation.md) for the tested path and remaining limits.
