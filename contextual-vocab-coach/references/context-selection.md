# Context intake and candidate selection

Read this reference when establishing or updating a goal, background card, source, or candidate set.

## Separate the three contexts

| Context | Question it answers | Reliable inputs |
|---|---|---|
| Need | What is worth learning now? | Recurring real contexts, near-term task, selected source, optional explicit goal |
| Familiarity | What can make it memorable? | Confirmed experiences, interests, known vocabulary |
| Ability | What is actually weak? | Retrieval attempts, comprehension checks, review history |

The first two can come from authorized conversations or documents. The third must primarily come from learner behavior. English written by an assistant is not evidence that the learner can produce it.

The learner does not need a narrow goal. A recurring real context can establish relevance without being promoted into a personal objective.

## Build the background card

Keep one stable learning direction in the learning surface, while preserving multiple context workspaces discovered from the learner's tasks. The default direction is helping the learner express what they already do in daily work and life. Switching context workspaces must not rewrite that direction. Include:

- Stable direction, and a narrower goal only when the learner explicitly states or confirms it.
- Success definition observable in a new situation when an explicit goal exists.
- Active context focus, such as product building or embodied AI; label it as context, not goal.
- Required modes: recognition, production, or listening.
- Familiar contexts that are safe and useful as memory anchors.
- Preferences such as time available and explanation language.
- Exclusions, including topics the learner says are irrelevant or private.
- Source labels and whether each field is confirmed or inferred.
- Coverage counts: all discovered tasks, titled tasks, and tasks inspected beyond metadata.

Do not persist an inferred sensitive fact. Present it for confirmation or omit it.

## Select candidates

Rank with judgment rather than fake precision. A strong candidate:

1. Directly helps the active context or task.
2. Is reusable beyond one sentence.
3. Matches the required mode and expected level.
4. Is not already marked known or not now.
5. Can be explained with a concise, task-relevant sense.

Include verbs, collocations, sentence frames, and connectors when they are more useful than domain nouns. Avoid long pre-generated word books. Default to 5–8 candidates per topic workspace.

Each candidate must carry:

- `term`: the English word or expression.
- `meaning`: one concise meaning in the current task.
- `kind`: `word`, `phrase`, `collocation`, or `sentence_frame`.
- `rationale`: why this helps now.
- `target_modes`: one or more of `recognition`, `production`, `listening`.
- `source_ids`: authorized sources that support relevance.
- `priority`: 1–5, used only for ordering.
- Optional `anchor`, `contrast`, and `evidence_summary`; keep them minimal and non-sensitive.

## Apply a pack

Create a temporary JSON file shaped like this, then validate with `apply-pack --dry-run` before applying:

```json
{
  "profile": {
    "goal": {
      "statement": "Express what I do in everyday work and life in English",
      "success_definition": "Recall useful English directly in familiar real situations instead of translating line by line",
      "focus_modes": ["production", "recognition"],
      "confirmed": true
    },
    "familiar_contexts": [
      {
        "label": "product development",
        "confidence": "confirmed",
        "source_ids": ["product-chat"]
      }
    ],
    "preferences": {"daily_minutes": 10, "explanation_language": "zh-CN"},
    "exclusions": ["client names"]
  },
  "sources": [
    {
      "source_id": "product-chat",
      "label": "Selected product discussion",
      "kind": "current_conversation",
      "locator": "current conversation",
      "authorized": true,
      "retain_raw": false,
      "summary": "The learner wants to explain a food-analysis product.",
      "status": "active"
    }
  ],
  "candidates": [
    {
      "term": "estimate portion sizes",
      "meaning": "估算每份食物的分量",
      "kind": "phrase",
      "rationale": "Needed to explain the product's image-analysis feature",
      "target_modes": ["production"],
      "source_ids": ["product-chat"],
      "priority": 5,
      "anchor": "describing a meal photo in the learner's own demo"
    }
  ]
}
```

The store merges by normalized term and sense. Re-importing context must preserve decisions and review history.
