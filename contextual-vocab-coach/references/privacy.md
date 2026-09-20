# Privacy and source boundaries

Read this reference before using a conversation, transcript, file, folder, or other personal context.

## Default boundary

Use only material the learner explicitly selected or the current conversation when the request clearly scopes it in. Do not discover and scan unrelated chat histories, home folders, cloud drives, or messaging databases.

Store a minimal source label and summary rather than raw content. Set `retain_raw` to false unless the learner explicitly asks to retain the original. A local script can still send data away if another command calls a cloud model; disclose that before such a call.

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
- Pause a source so it stops contributing new candidates.
- Delete source metadata while keeping explicitly accepted learning records.
- Purge source-derived candidates, accepted items, and their review events.

Use `source-status`, `source-delete --mode metadata`, or `source-delete --mode purge` as described in the CLI reference. Explain the consequence before a purge.

