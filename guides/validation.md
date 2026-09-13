# Router validation

[Back to Claude + Astra Router](../README.md)

Checked on 13 September 2026 on macOS. Local versions: Claude Code 2.1.270 and Codex CLI 0.154.0. The worker model was explicitly requested as `gpt-6-astra`.

## Actual Claude → Astra → Claude → Astra run

The lead ran Claude Code in an isolated local Git folder containing only the runner and fictional source pack. Claude received the same routing instruction template explicitly in its instructions. Claude's safe mode disabled unrelated customisations while retaining normal authentication and tool permissions; this trial did not test automatic discovery of an installed project `CLAUDE.md`.

The observed sequence was:

1. Claude read the fictional sources and wrote a complete worker brief with the source text embedded.
2. Claude invoked `scripts/astra.py run`. Codex returned an Astra answer and a recorded session ID.
3. Claude inspected the actual result against the sources and wrote review findings. The first answer passed those factual checks.
4. As a deliberate test of revision, Claude requested a reporting-date heading with an otherwise unchanged body.
5. Claude invoked `scripts/astra.py revise`. It resumed the exact recorded session with `gpt-6-astra` and the same read-only sandbox.
6. Claude read the second result and metadata and returned its verification summary. The lead then checked the records and compared both outputs independently.

Both calls returned success and `turn.completed`. Session IDs, model and sandbox matched. The revised output was exactly the requested heading plus the original 145-word/item body, including source labels. The sources and runner were unchanged. No tool actions were taken by the Astra worker itself in this text-only trial.

[Read the actual revised output](../examples/weekly-update/router-observed.md).

Non-blocking local configuration warnings appeared in the worker logs, including a local connector startup issue. They did not prevent the text task from completing. The runner rejects terminal errors, failed turns, missing completion, missing output and mismatched resumed sessions. It records item-level diagnostic messages in the event log for Claude to inspect; it does not classify every diagnostic as a fatal error.

## Script tests

Ten automated tests mock the Codex subprocess. They check:

- Literal prompt input and paths with spaces, without shell interpolation.
- Fixed Astra model and read-only default.
- Exact session reuse and sandbox preservation on revision.
- Existing-run protection, concurrent-revision lock and two-revision limit.
- Missing session, missing or empty output, nonzero exit and launch failure.
- Required terminal completion, terminal errors and mismatched resumed IDs.
- Immutable prompt snapshots and separation of failed results from successful ones.

Run them with `python3 -m unittest discover -s tests -v`. They passed for this release. Local links, syntax and staged diff checks were also inspected before publication.

## Supporting exercise, separate from the router test

The earlier manual exercise used a Terra agent to review and repair an intentionally flawed draft without the answer key in its supplied context. It found all six seeded issue groups. Its [107-word/item output](../examples/weekly-update/observed-trial.md) and the [illustrative answer key](../examples/weekly-update/corrected-update.md) remain available as supporting material. That exercise alone does not validate Claude-to-Astra routing.

## Limits

This was one text-only integration trial with one planned revision. It did not test workspace-write execution, Windows, a novice's setup experience, every account's model access, cost savings, automatic project-template discovery, or long-running recovery after crashes. A failed worker may have made partial changes in workspace-write mode; inspect the project before retrying.

A successful process and review still need a person's acceptance decision. The [real editorial correction](real-correction.md) illustrates that review standard using a different earlier task; it is not retroactive proof that the router ran in that task.
