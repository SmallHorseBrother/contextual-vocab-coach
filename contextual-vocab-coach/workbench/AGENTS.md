# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Selected product direction

- Recreate the selected “Codex Sidecar” concept from `../../../design/reference-codex-sidecar.png`.
- Desktop-first, Chinese-first, local-first. Codex history is optional. Users without Codex can type, dictate, paste, or import text and append to a named source; the workbench owns candidate decisions, learning sessions, review, and source controls.
- The complete personal vocabulary inventory is the default and highest-fidelity screen. Preserve its warm ivory surface, serif learning-direction title, restrained teal accent, three-column frame, searchable vocabulary grid, and right assistant rail.
- Avoid gamification, brain-scan claims, decorative analytics, card overload, gradients, and invented cloud/account features.
- Merge foundational and context-specific expressions into one searchable personal inventory while preserving provenance. Context filters and source details are secondary controls; any entry can be deliberately added to learning, but the inventory is never bulk-scheduled.
- A no-Codex newcomer lands in "我的上下文". Use 500, 1000, and 2000+ (2500 actual) ranked views over one larger offline lexicon. More words means broader, more detailed recommendations, not an assertion that every word came from the supplied text. Adding context reorders the inventory without resetting learning progress; raw user passages are not persisted.
- A review rating must always produce visible feedback. Single-item sessions end on a completion state instead of silently cycling to the same card; multi-item sessions advance once; `again` visibly resets the same item for another attempt; save failures stay on the answer with a retryable error. Keep recognition, production, and listening prompts visibly distinct, and return learners to the surface where they started.
- The learner's stable direction is to express everyday real contexts in English. The initial scan covers every available task and streams every user-authored message locally. “Update vocabulary” processes the newest new or changed tasks first, reuses unchanged derived results, expands the inventory, and preserves learner decisions and review history.
- Topic clusters such as embodied AI or product building are hidden classification and traceability metadata, never inferred personal goals or required navigation. The default inventory spans all contexts.
- Demo data must always be visibly labeled. Never imply that a fixed sample or fallback state came from the learner's Codex history.
- The selected third visual direction is a growing personal knowledge graph, not a static list disguised as a map. Use the organic multi-domain network, warm ivory/navy/teal language, graph controls, and an evidence inspector. Include all inventory nodes in the underlying graph while showing a readable overview by default.
- When a new expression enters, show it separately as fresh and propose only evidence-labeled relationships to existing expressions. Allow the learner to accept, ignore, or retype weak connections. Marking a term as seen removes its fresh badge but does not change mastery, add it to review, or delete its graph node.
