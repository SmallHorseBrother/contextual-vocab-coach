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
