# Validation for the initial release

[Back to the guide](../README.md)

Checked on 13 September 2026. The practice scenario deliberately uses a fictional 14 September reporting date.

## What was run

A Terra (`gpt-5.6-terra`) subagent received only the three prompts, fictional sources and intentionally flawed draft. It did not receive the expected-review or corrected-update answer keys. It reviewed the faulty draft, then performed one revision in the same agent context.

The run found all six issue groups in the answer key: unconfirmed ownership, invented approval, an obsolete unconditional start date, misrepresented panel action, hidden decisions and missing source labels. Its revised update retained the security dependency and unknown commercial approval status. The lead compared those results with the original sources.

The returned update contained 107 whitespace-separated words/items including source labels, under the 180-word limit. The agent's own reported count was 104; the lead corrected the count by computation. The model's self-report was not used as the check.

[Read the actual returned update](../examples/weekly-update/observed-trial.md).

## What was inspected

- The illustrative answer key against the complete source pack.
- The original personal editorial sentence, dated QA finding and revised wording used in the real case note.
- The complete handover inputs and source labels in the instructions.
- Relative links, repository contents and the distinction between original records, fictional examples and observed trial output.

Sol performed a separate documentation review. Two findings were corrected: the optional delegated revision now explicitly includes the complete original brief, sources, draft and review; the answer key separates the final human decisions with precise source labels. The blind run had already received full inputs, so these documentation corrections did not change its source facts or result.

## What this does not establish

This was one model-run trial of the deliberately faulty review/revision path. It was not a novice usability study, a test of every listed AI product, or a benchmark of model quality, speed or cost. The reviewer and reviser shared one agent context during that trial; it does not validate independence between those roles.

The fresh-writer path and the complete optional Codex orchestration request were not exercised end to end for this release. They remain instructions to try in your own permitted environment. A successful exercise does not make real work safe to use without its own review.
