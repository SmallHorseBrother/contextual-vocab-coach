---
name: contextual-vocab-coach
description: Build and update a broad personal English vocabulary inventory from user-supplied writing or speech, optional local Codex history, and everyday language, then run a smaller retrieval and review loop. Use when a learner wants a controllable 500/1000/2500-word recommendation list, no-Codex onboarding, incremental context updates, source traceability, a knowledge graph, active practice, or review.
---

# Contextual Vocab Coach

Help the learner answer three questions: what English is worth learning now, how to connect it to their world, and when to retrieve it again. The differentiator is the first two; use the included scheduler as a conservative baseline rather than claiming a novel memory algorithm.

## Route the request

- For an initial vocabulary build, incremental Codex scan, optional goal, selected conversation, pasted text, or authorized file, read [references/context-selection.md](references/context-selection.md) and [references/privacy.md](references/privacy.md).
- For learning or review, read [references/session-design.md](references/session-design.md).
- Before reading or changing persistent state, read [references/store-cli.md](references/store-cli.md).
- For basic everyday vocabulary, search the bundled starter and expanded lexicons before inventing a generic list. Treat them as a broad reservoir, not evidence that every entry is unknown or due. The expanded ECDICT-derived senses and difficulty hints need context-sensitive checking.
- When the learner asks for a visual interface, complete word list, or workbench, start the bundled local workbench after reading the store reference. Open its loopback URL in an available browser surface and keep the server running for the learner's session.
- When the learner asks about the knowledge graph, new-word attachment, or relation review, use the workbench's graph view. Explain that freshness and mastery are separate: seeing a new node removes its new badge but never marks it known or schedules review. Explain that relation scores are local heuristic clues, not calibrated probabilities or model-derived synonyms.
- For status, show the task-to-vocabulary mastery view from the store. Do not invent a neurological or cognitive diagnosis.
- For pause, deletion, or source inspection, follow the privacy operations in the store reference.

## Non-negotiable distinctions

1. Build one broad personal vocabulary inventory by default. Context is hidden organizational metadata for ranking, filtering, and traceability; do not require the learner to choose a context before viewing or learning words.
   A learner without Codex can start immediately: run the workbench with `--no-context-scan`, import a 20–12000-character passage through "我的上下文", and append more later. The user may choose a 500, 1000, or 2500-item recommendation view without changing the study queue.
2. Do not require the learner to invent a narrow goal. Default to helping them express the work and life contexts they actually encounter. Treat current tasks as relevance contexts, and create a narrower goal only when the learner explicitly states one.
3. Preserve words, phrases, collocations, and connective language that help complete the task. Do not over-select specialist nouns.
4. Personal context helps encode a memory. A later test must change the wording or situation so recall is not tied to one story.
5. Combine several weak items only when the resulting situation is natural. Split awkward combinations.
6. Do not treat assistant-authored text, quoted material, or speculation as a fact about the user. Label practice scenarios as hypothetical when they are not confirmed events.
7. New context may update candidates and topic assignments, but it must not silently rewrite the learner's stable direction or an explicit goal. It also must not erase accepted items, review history, or decisions such as `known` and `not_now`.
8. The personal inventory may present foundational and context-specific expressions together, but preserve their provenance. Building a large inventory is allowed; scheduling it all is not. An entry enters the learning loop only after an explicit learner decision.
9. On the initial build, cover every available Codex task with full metadata indexing and stream every user-authored message locally. Cache only derived, non-raw results. On update, process newest changed or added tasks first and reuse unchanged results. Do not treat assistant or tool output as learner evidence.
10. Keep task domains as optional many-to-many classifications. They must not be the default navigation, restrict the complete inventory, rewrite the stable learning direction, or erase decisions and review history.
11. In the knowledge graph, infer only relationships supported by shared meanings, expression composition, task co-occurrence, or labeled topical/scenario clues. Preserve human accept, ignore, and relation-type decisions across updates. Do not force an edge for a node with insufficient evidence. When the learner adds an expression manually, keep it out of the review queue until they explicitly choose to study it.

## Default workflow

1. Inspect existing state with `status`. If none exists, initialize it.
2. When Codex history is available and scanning is enabled, perform an initial local-only scan of every available active and archived task unless the learner narrows or pauses it. Index all titles and timestamps, stream every user-authored message from every rollout, cache only derived classifications and vocabulary links, and show exact coverage and bytes indexed. Without Codex, open the context composer instead and never represent the bundled dictionary as scanned personal history.
3. Materialize one static personal vocabulary snapshot after source intake. Merge broad foundational English, directly observed expressions, and context-specific words and phrases. Preserve source and classification metadata without showing it by default. Offer 500/1000/2500 as ranked views over the same larger offline pool.
4. On an explicit Codex update, scan newest tasks first and reread only new or changed rollouts. On a manual update, append the new text to the named personal source and rerank the snapshot. In either case preserve `known`, `not_now`, accepted items, and review history; never persist the raw manual passage.
5. Do not cap the inventory at 5–8 items per topic. Generate and retain as many defensible expressions as the authorized sources support, deduplicate senses, and rank them. Keep only the active learning and review queue small.
6. Let the learner mark each candidate `known`, `not_now`, `test`, or `learning`. If the learner asked to start immediately, test uncertain items instead of silently asserting ignorance.
7. Teach 3–5 accepted weak items using a familiar anchor, clear meaning, contrast when useful, and active retrieval. Do not reveal the answer during the retrieval attempt.
8. Record the actual feedback and response time. Never record success merely because the learner read the explanation.
9. On later sessions, serve due items first, change the test context, and then add at most a small number of new candidates.
10. End with a compact summary: what was learned, what is due next, and one real task in which to use it.

When a visual surface is useful, show the context composer first to a new user without Codex, then the complete personal vocabulary view with search and an update action. Context filters and source details are optional secondary controls. The workbench and CLI share the same local store; do not duplicate or re-import state just to open the interface.

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
