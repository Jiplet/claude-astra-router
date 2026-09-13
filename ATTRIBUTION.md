# Attribution

This project was prompted by [The Actionable AI's Route Astra guide](https://theactionableai.com/guides/route-astra-guide/read), read on 13 September 2026. That guide describes Claude Code directing work to Astra through Codex, reviewing the returned work and sending fixes back.

Claude + Astra Router is an independent implementation by Jacob / Jiplet. Its Python runner, Claude instruction template, examples and wording were written for this repository. The source's routing block and shell commands were not copied. This implementation uses explicit task records and recorded session IDs for revision; it does not assume a particular subscription tier or reproduce employee-cost comparisons.

The manual review prompts are supporting exercises. The dated validation record distinguishes those exercises from tests of the Claude Code → Codex CLI → Astra connection.

Implementation references, checked 13 September 2026:

- [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode): CLI calls, JSON event stream, result files and explicit-session resume.
- [Codex CLI](https://learn.chatgpt.com/docs/cli): installation entry point.
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works): terminal tools and project instructions.
- [Claude Code quickstart](https://code.claude.com/docs/en/quickstart): installation and sign-in entry point.

The real editorial correction uses short excerpts from Jacob's own planning records. The broader OS teaser is Jacob's supplied description and intention, not a dated release commitment or validation claim.

No affiliation or endorsement by the source publisher or AI providers is implied. Product and model names belong to their respective owners. The MIT licence covers this repository's original work, not linked third-party material.
