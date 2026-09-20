# Local store CLI

Read this reference before inspecting or changing persistent learning state.

The script uses only the Python standard library. By default it stores data outside project repositories:

- Windows: `%LOCALAPPDATA%\contextual-vocab-coach\state.json`
- macOS/Linux: `$XDG_DATA_HOME/contextual-vocab-coach/state.json` or `~/.local/share/contextual-vocab-coach/state.json`

Override with `CONTEXTUAL_VOCAB_HOME` or `--store <directory-or-json-file>`. Tests and demos must always use an isolated temporary store.

Run commands from the skill directory:

```text
python scripts/vocab_store.py init
python scripts/vocab_store.py status --format markdown
python scripts/vocab_store.py apply-pack --input <pack.json> --dry-run
python scripts/vocab_store.py apply-pack --input <pack.json>
python scripts/vocab_store.py decide --item <id-or-exact-term> --decision learning
python scripts/vocab_store.py due --limit 5
python scripts/vocab_store.py review --item <id-or-exact-term> --mode production --feedback good --response-ms 4200 --strategy personal-scene --personalized --transfer-test
python scripts/vocab_store.py source-status --source-id <id> --status paused
python scripts/vocab_store.py source-delete --source-id <id> --mode metadata
python scripts/vocab_store.py doctor
```

## Operational rules

- Run `status` before starting a session.
- Validate generated packs with `--dry-run` before applying them.
- Resolve an item by ID when two senses share the same term.
- Use `decide` to preserve `known` and `not_now` decisions across future imports.
- Run `due` before introducing new items.
- Call `review` only after the learner attempts retrieval.
- `source-delete --mode metadata` removes the source, its summaries, links, and source-only inferred anchors while preserving accepted learning items and review schedules.
- `source-delete --mode purge` also removes items supported only by that source and their review events. Treat it as destructive and use only on an explicit request.
- Run `doctor` after any failed or interrupted state-changing command.

The CLI writes state atomically. It emits JSON unless a command explicitly requests Markdown.

