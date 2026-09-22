# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Selected product direction

- Recreate the selected “Codex Sidecar” concept from `../../../design/reference-codex-sidecar.png`.
- Desktop-first, Chinese-first, local-first. Codex supplies authorized context; the workbench owns candidate decisions, learning sessions, review, and source controls.
- The candidate inbox is the default and highest-fidelity screen. Preserve its warm ivory surface, serif goal title, restrained teal accent, three-column frame, grouped table rows, and right assistant rail.
- Avoid gamification, brain-scan claims, decorative analytics, card overload, gradients, and invented cloud/account features.
- Keep a broad starter reservoir (hundreds of basic words and everyday expressions) separate from the small 5–8 item contextual inbox. The library must be searchable and filterable by everyday scenario and approximate level, and any entry can be deliberately added to learning.
- A review rating must always produce visible feedback. Single-item sessions end on a completion state instead of silently cycling to the same card; multi-item sessions advance once; `again` visibly resets the same item for another attempt; save failures stay on the answer with a retryable error. Keep recognition, production, and listening prompts visibly distinct, and return learners to the surface where they started.
- The native product should aggressively index local Codex task history by default, expose exact coverage and scan depth, cluster tasks into separate topic workspaces, and make topic switching change the active goal and candidate inbox without erasing cross-topic learning history.
- Demo data must always be visibly labeled. Never imply that a fixed sample or fallback state came from the learner's Codex history.
