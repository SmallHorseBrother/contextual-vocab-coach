---
name: contextual-vocab-coach
description: Build and update a broad personal English vocabulary inventory from local Codex history, everyday language, user-selected sources, and optional goals, then run a smaller retrieval and review loop from that inventory. Use when a learner wants a full generated word list, incremental rescanning, source traceability, contextual filtering, active practice, or review. Not for generic exam drilling disconnected from real use.
---

# Contextual Vocab Coach

Help the learner answer three questions: what English is worth learning now, how to connect it to their world, and when to retrieve it again. The differentiator is the first two; use the included scheduler as a conservative baseline rather than claiming a novel memory algorithm.

## Route the request

- For an initial vocabulary build, incremental Codex scan, optional goal, selected conversation, pasted text, or authorized file, read [references/context-selection.md](references/context-selection.md) and [references/privacy.md](references/privacy.md).
- For learning or review, read [references/session-design.md](references/session-design.md).
- Before reading or changing persistent state, read [references/store-cli.md](references/store-cli.md).
- For basic everyday vocabulary, search the bundled starter lexicon before inventing a generic list. Treat it as a broad reservoir, not evidence that every entry is unknown or due.
- When the learner asks for a visual interface, complete word list, or workbench, start the bundled local workbench after reading the store reference. Open its loopback URL in an available browser surface and keep the server running for the learner's session.
- For status, show the task-to-vocabulary mastery view from the store. Do not invent a neurological or cognitive diagnosis.
- For pause, deletion, or source inspection, follow the privacy operations in the store reference.

## Non-negotiable distinctions

1. Build one broad personal vocabulary inventory by default. Context is hidden organizational metadata for ranking, filtering, and traceability; do not require the learner to choose a context before viewing or learning words.
2. Do not require the learner to invent a narrow goal. Default to helping them express the work and life contexts they actually encounter. Treat current tasks as relevance contexts, and create a narrower goal only when the learner explicitly states one.
3. Preserve words, phrases, collocations, and connective language that help complete the task. Do not over-select specialist nouns.
4. Personal context helps encode a memory. A later test must change the wording or situation so recall is not tied to one story.
5. Combine several weak items only when the resulting situation is natural. Split awkward combinations.
6. Do not treat assistant-authored text, quoted material, or speculation as a fact about the user. Label practice scenarios as hypothetical when they are not confirmed events.
7. New context may update candidates and topic assignments, but it must not silently rewrite the learner's stable direction or an explicit goal. It also must not erase accepted items, review history, or decisions such as `known` and `not_now`.
8. The personal inventory may present foundational and context-specific expressions together, but preserve their provenance. Building a large inventory is allowed; scheduling it all is not. An entry enters the learning loop only after an explicit learner decision.
9. On the initial build, cover every available Codex task with full metadata indexing and bounded content inspection. Cache derived, non-raw results. On update, process newest changed or added tasks first and reuse unchanged results. Never claim bounded inspection is a full reading of every byte.
10. Keep task domains as optional many-to-many classifications. They must not be the default navigation, restrict the complete inventory, rewrite the stable learning direction, or erase decisions and review history.

## Default workflow

1. Inspect existing state with `status`. If none exists, initialize it.
2. When running inside Codex Desktop or the local workbench, perform an initial local-only scan of every available active and archived task unless the learner narrows or pauses it. Index all titles and timestamps, inspect a bounded head/tail window from every rollout, cache only derived classifications and vocabulary links, and show exact coverage.
3. Materialize one static personal vocabulary snapshot after the scan. Merge broad foundational English, directly observed known expressions, and context-specific words and phrases. Preserve source and classification metadata without showing it by default.
4. On an explicit update, scan newest tasks first, reread only new or changed rollouts, expand the snapshot, and preserve `known`, `not_now`, accepted items, and review history.
5. Do not cap the inventory at 5–8 items per topic. Generate and retain as many defensible expressions as the authorized sources support, deduplicate senses, and rank them. Keep only the active learning and review queue small.
6. Let the learner mark each candidate `known`, `not_now`, `test`, or `learning`. If the learner asked to start immediately, test uncertain items instead of silently asserting ignorance.
7. Teach 3–5 accepted weak items using a familiar anchor, clear meaning, contrast when useful, and active retrieval. Do not reveal the answer during the retrieval attempt.
8. Record the actual feedback and response time. Never record success merely because the learner read the explanation.
9. On later sessions, serve due items first, change the test context, and then add at most a small number of new candidates.
10. End with a compact summary: what was learned, what is due next, and one real task in which to use it.

When a visual surface is useful, default to the complete personal vocabulary view with search and an update action. Context filters and source details are optional secondary controls. The workbench and CLI share the same local store; do not duplicate or re-import state just to open the interface.

The workbench's Word Library contains a curated starter reservoir across everyday scenarios. Its A1/A2/B1 labels are approximate practical hints for filtering, not official CEFR assessments. Searching or viewing an entry must never create a review item; use `lexicon-add` or the visible add action only after the learner chooses it.

Match the user's language for explanations. Keep the target English natural and idiomatic. If a proposed phrase is unnatural or its sense is ambiguous, correct it before saving it.

## Output contracts

For inventory intake, show the total vocabulary count, scan coverage, update result, and searchable word list. Keep `source`, `context`, and evidence available on demand rather than occupying the default learning surface.

For a learning session, use this sequence:

1. Meaning and personal connection.
2. One natural example or short scene.
3. Retrieval without the answer.
4. Feedback after the attempt.
5. A transfer test in a changed context when appropriate.

For a mastery view, group items by the active task and show `candidate`, `learning`, `due`, `recently passed`, `known`, and `not now`. Describe it as a learning record, not a scan of the learner's mind.
