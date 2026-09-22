# Privacy and source boundaries

Read this reference before using a conversation, transcript, file, folder, or other personal context.

## Default boundary

When the learner opens the native local workbench or asks for Codex-wide context, treat the local Codex task history as the default source scope. Index task titles and timestamps across active and archived tasks, and use bounded local reads for recent task content. Show exactly how many tasks were discovered, titled, and more deeply inspected.

Do not expand this default to unrelated home folders, cloud drives, browsers, or messaging databases. When the learner explicitly narrows the task scope, honor that narrower boundary.

Store a minimal task identifier, title, topic assignment, source label, and summary rather than raw content. Set `retain_raw` to false unless the learner explicitly asks to retain the original. The bundled scanner is deterministic and local-only; if another command would send conversation text to a remote model, disclose that separately before the call.

## Source truth

Distinguish:

- User statements.
- Assistant suggestions.
- Quoted or pasted third-party material.
- Inferences.

Only a user-confirmed statement is a durable personal fact. Do not turn a one-off topic into a permanent interest or learning goal.

## Controls

The learner must be able to:

- Inspect source labels and summaries.
- Inspect context coverage, topic assignments, and whether a task received metadata-only or deeper analysis.
- Pause a source so it stops contributing new candidates.
- Delete source metadata while keeping explicitly accepted learning records.
- Purge source-derived candidates, accepted items, and their review events.

Use `source-status`, `source-delete --mode metadata`, or `source-delete --mode purge` as described in the CLI reference. Explain the consequence before a purge.
