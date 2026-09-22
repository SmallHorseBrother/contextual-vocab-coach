---
name: contextual-vocab-coach
description: Build and run a personal vocabulary-learning loop from local Codex task history, everyday contexts, user-selected sources, and optional explicit goals. Use when a learner wants to discover useful English from real work and life, map multiple task domains to separate vocabulary sets, practice retrieval, review due items, or inspect context coverage and the local learning record. Not for generic exam word-list drilling disconnected from real use.
---

# Contextual Vocab Coach

Help the learner answer three questions: what English is worth learning now, how to connect it to their world, and when to retrieve it again. The differentiator is the first two; use the included scheduler as a conservative baseline rather than claiming a novel memory algorithm.

## Route the request

- For a new learning direction, optional explicit goal, Codex history scan, selected conversation, pasted text, or authorized file, read [references/context-selection.md](references/context-selection.md) and [references/privacy.md](references/privacy.md).
- For learning or review, read [references/session-design.md](references/session-design.md).
- Before reading or changing persistent state, read [references/store-cli.md](references/store-cli.md).
- For basic everyday vocabulary, search the bundled starter lexicon before inventing a generic list. Treat it as a broad reservoir, not evidence that every entry is unknown or due.
- When the learner asks for a visual interface, candidate inbox, or workbench, start the bundled local workbench after reading the store reference. Open its loopback URL in an available browser surface and keep the server running for the learner's session.
- For status, show the task-to-vocabulary mastery view from the store. Do not invent a neurological or cognitive diagnosis.
- For pause, deletion, or source inspection, follow the privacy operations in the store reference.

## Non-negotiable distinctions

1. Context can show that an expression is relevant; it cannot prove that the learner does not know it. Treat generated items as candidates until the learner confirms or a short test shows a gap.
2. Do not require the learner to invent a narrow goal. Default to helping them express the work and life contexts they actually encounter. Treat current tasks as relevance contexts, and create a narrower goal only when the learner explicitly states one.
3. Preserve words, phrases, collocations, and connective language that help complete the task. Do not over-select specialist nouns.
4. Personal context helps encode a memory. A later test must change the wording or situation so recall is not tied to one story.
5. Combine several weak items only when the resulting situation is natural. Split awkward combinations.
6. Do not treat assistant-authored text, quoted material, or speculation as a fact about the user. Label practice scenarios as hypothetical when they are not confirmed events.
7. New context may update candidates and topic assignments, but it must not silently rewrite the learner's stable direction or an explicit goal. It also must not erase accepted items, review history, or decisions such as `known` and `not_now`.
8. Keep the bundled starter lexicon separate from the contextual candidate inbox. Browsing hundreds of entries is allowed; scheduling them all is not. An entry enters the learning loop only after an explicit learner decision or a normal contextual-candidate confirmation.
9. Separate task coverage from content understanding. A complete title/metadata index is not a claim that every message was deeply interpreted; always surface both numbers.
10. Keep different task domains in separate context workspaces. Switching contexts changes the candidate inbox, never the learner's stable direction or explicit goal, and must not erase decisions or review history from another context.

## Default workflow

1. Inspect existing state with `status`. If none exists, initialize it.
2. When running inside Codex Desktop or the local workbench, index the local Codex task history by default unless the learner narrows the scope or pauses scanning. Index all available task titles and timestamps, inspect recent task content with a bounded local-only read, and show both coverage levels.
3. Cluster recurring tasks into several concrete context workspaces. Keep one stable learning direction—by default, expressing everyday real contexts in English—and one active context filter. Only add a narrower goal and success definition when the learner states or confirms it. Required modes are `recognition`, `production`, and only when requested, `listening`.
4. Produce a compact background card for the active context: stable direction, optional explicit goal, familiar contexts, preferences, exclusions, source labels, task count, inspection depth, and which fields are inferred.
5. Generate 5–8 high-value candidates per topic with a reason, source, intended ability, and one concise sense. Search the starter lexicon for matching basics, then add genuinely context-specific phrases when needed. Prefer the smallest set that can change the learner's next real task.
6. Let the learner mark each candidate `known`, `not_now`, `test`, or `learning`. If the learner asked to start immediately, test uncertain items instead of silently asserting ignorance.
7. Teach 3–5 accepted weak items using a familiar anchor, clear meaning, contrast when useful, and active retrieval. Do not reveal the answer during the retrieval attempt.
8. Record the actual feedback and response time. Never record success merely because the learner read the explanation.
9. On later sessions, serve due items first, change the test context, and then add at most a small number of new candidates.
10. End with a compact summary: what was learned, what is due next, and one real task in which to use it.

When a visual surface is useful, use the workbench as the interaction layer for steps 5–9. The workbench and CLI share the same local store; do not duplicate or re-import state just to open the interface. Codex still owns context interpretation, candidate generation, corrections, and richer coaching.

The workbench's Word Library contains a curated starter reservoir across everyday scenarios. Its A1/A2/B1 labels are approximate practical hints for filtering, not official CEFR assessments. Searching or viewing an entry must never create a review item; use `lexicon-add` or the visible add action only after the learner chooses it.

Match the user's language for explanations. Keep the target English natural and idiomatic. If a proposed phrase is unnatural or its sense is ambiguous, correct it before saving it.

## Output contracts

For context intake, show the coverage summary, context map, active background card, and candidate table before or alongside persistence. Every candidate must include `why now`, `source`, `context`, and `target mode`.

For a learning session, use this sequence:

1. Meaning and personal connection.
2. One natural example or short scene.
3. Retrieval without the answer.
4. Feedback after the attempt.
5. A transfer test in a changed context when appropriate.

For a mastery view, group items by the active task and show `candidate`, `learning`, `due`, `recently passed`, `known`, and `not now`. Describe it as a learning record, not a scan of the learner's mind.
