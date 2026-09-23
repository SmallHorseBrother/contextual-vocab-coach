# Knowledge graph design QA

**Source visual truth:** selected concept 3, generated in the local design session (not bundled with the public repository).

**Implementation screenshot:** local QA capture `contextual-vocab-graph-qa.jpg` (not bundled; real local workbench, map overview).

**Viewport and normalization:** source 1487 × 1058 px, illustrative desktop @1x; browser CSS viewport 1910 × 1075 at device scale 1.34, Codex in-app capture saved at 1888 × 1062 px. The IAB viewport override did not resize the existing tab, so comparison uses proportional app regions, not pixel-precise coordinates. Both images were opened together. The source depicts an illustrative *new-word* state; the real-data screenshot depicts the baseline *no new word* state. New-word and before/after states were separately verified in an isolated demo tab. This state mismatch is not used to infer missing functionality.

## Findings

No actionable P0/P1/P2 differences remain. The final implementation preserves the three-column frame, warm ivory surface, Chinese serif direction title, teal controls, organic colored domain regions, network connections, right-side evidence inspector, and timeline controls. The underlying graph contains all 592 personal vocabulary records; the readable first view shows 42 without deleting the rest.

P3 follow-up: the mock includes a minimap and bilingual captions directly on more graph nodes. The implementation instead provides search, fit/zoom, and the bilingual inspector. A minimap can be added if navigation of the full-density view becomes cumbersome.

## Required fidelity surfaces

- **Typography:** serif direction title and compact sans-serif UI match the source hierarchy. Final graph overview moved domain headings left of the clusters, resolving collisions with the highest-priority vocabulary labels. Long phrases still wrap; inspector carries full text.
- **Spacing/layout:** sidebar, central canvas, and right inspector retain source order and proportions. The live desktop is wider than the source mock, so graph clusters are spread across seven actual domains rather than five illustrative ones. Controls remain visible above the canvas.
- **Colors/tokens:** warm off-white, navy, teal, amber, blue, and violet map to the reference. Blue is reserved for genuinely new nodes and suggested edges; baseline has none.
- **Image quality/assets:** the central visual is an interactive Cytoscape graph with library-generated BubbleSets contours, not a flattened screenshot or hand-drawn decorative substitute. Phosphor icons match the existing workbench icon family. No mock-specific raster asset is required for the graph itself.
- **Copy/content:** labels describe real local data and heuristic evidence. The UI says “规则线索” rather than a calibrated confidence probability; it does not claim a generic same-domain link means synonymy. The demo banner is explicit.
- **Interaction/accessibility:** search, density, domain and relation filters, pan/zoom/fit, new-expression form, accept/ignore/change-type, mark-seen, and before/after were exercised. Browser error log: empty. Controls have accessible labels and no hidden primary action at the tested desktop viewport.

## Comparison history

1. Initial implementation used Cytoscape compound-node outlines that read as rectangular boxes rather than the selected organic network. Replaced them with library-generated BubbleSets contours. Browser post-fix capture showed curved colored clusters and cross-domain edges.
2. First BubbleSets overview displayed 77 then 56 nodes, causing small labels and collisions with domain headings. Reduced overview to six priority nodes per domain (42 total) and placed domain headings outside the term centers. Final visual evidence is the implementation screenshot above; `deployment pipeline`, domain headings, and the right inspector are now legible.
3. New-word state testing found an isolated term could have no supported links. The inspector now says so honestly; when a supported neighbor is added, a suggested edge appears. A second data-layer issue would have expanded unrelated old edges on every addition; incremental sync now limits new edges to newly added nodes. Four Python invariant tests and eight frontend/Sites tests pass.

**Final result: passed**
