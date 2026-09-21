# Design QA — Codex Sidecar workbench

final result: passed

## Evidence

- Source concept: `design/reference-codex-sidecar.png` (1489 × 1060)
- Browser capture: `design/implementation-codex-sidecar.jpg`
- Normalized comparison: `design/qa-side-by-side.png` (source and implementation at 1440 × 1024)
- Browser under test: Codex in-app browser, local production server at `http://127.0.0.1:4174/`

## Fidelity review

| Surface | Result | Evidence |
|---|---|---|
| Layout | Passed | Three-column desktop composition, navigation width, candidate table, goal header, and Codex assistant rail match the selected concept's hierarchy and content order. |
| Spacing | Passed | Row rhythm, section padding, separators, and assistant-card grouping remain visually equivalent after normalization. |
| Typography | Passed | Platform CJK serif/sans stacks preserve the concept's display/body contrast without shipping a 32 MB font payload. Long dynamic copy wraps without overlap. |
| Color and surfaces | Passed | Warm ivory paper, charcoal/navy text, restrained teal actions, subtle borders, and flat cards match the target intent; no gradients or decorative effects were added. |
| Icons | Passed | All interface icons use one Phosphor family with consistent stroke weight and alignment. No emoji, custom SVG, or CSS-drawn substitute icons are used. |
| Copy | Passed | The Chinese-first goal, source lineage, candidate rationales, assistant summary, and focus points are coherent outside the original conversation. |
| Imagery | Not applicable | The selected concept contains interface chrome and icons, not photographic or illustrative source assets. |

## Functional and state review

- Candidate decision persisted through the local JSON API; adding one two-mode item changed the review badge from 0 to 2.
- The 10-minute learning CTA opened an active-recall card, accepted an answer, revealed feedback only after submission, and persisted a `good` review; the due badge dropped from 2 to 1 because the second mode remains independently due.
- Sources could be paused and restored, and the assistant summary reacted to the authorization state.
- The mastery map grouped the reviewed item under learning and retained the other candidates.
- The goal disclosure opens and explains both the success criterion and how to change the goal in Codex.
- Browser console check returned no warnings or errors.

## Accessibility and resilience

- Semantic buttons, table/row structure, textarea labeling, focus rings, disabled submit state, and speech button labels are present.
- Icon-only navigation at narrow widths retains explicit accessible names.
- Desktop was checked at a 1440 × 1024 CSS viewport.
- Tablet check: 970 px CSS width, no horizontal overflow; navigation and assistant rail become document-flow sections.
- Mobile check: 597 px CSS width, no horizontal overflow; candidate rows collapse to a two-column layout and actions remain 300 px wide.

## Findings resolved during QA

1. **Candidate actions clipped at desktop width.** The seven-column minimums exceeded the center pane. Column constraints and the responsive grid were tightened so all four actions remain visible.
2. **Collapsed navigation lost accessible names.** Each navigation button now has an explicit `aria-label`.
3. **Goal chevron implied an inert control.** It now opens a real disclosure with the goal's success definition and a clear path for changing it.
4. **Bundled CJK fonts inflated the client from 266 KB to 32 MB.** Replaced them with platform CJK stacks; the final client contains three files totaling about 266 KB.

No blocking fidelity, interaction, accessibility, or responsiveness findings remain.
