# Context intake and candidate selection

Read this reference when establishing or updating a goal, background card, source, or candidate set.

## Separate the three contexts

| Context | Question it answers | Reliable inputs |
|---|---|---|
| Need | What is worth learning now? | Explicit goal, near-term task, selected source |
| Familiarity | What can make it memorable? | Confirmed experiences, interests, known vocabulary |
| Ability | What is actually weak? | Retrieval attempts, comprehension checks, review history |

The first two can come from authorized conversations or documents. The third must primarily come from learner behavior. English written by an assistant is not evidence that the learner can produce it.

## Build the background card

Keep one active goal in the first version. Include:

- Goal stated as a real outcome, such as “explain my product without translating sentence by sentence.”
- Success definition observable in a new situation.
- Required modes: recognition, production, or listening.
- Familiar contexts that are safe and useful as memory anchors.
- Preferences such as time available and explanation language.
- Exclusions, including topics the learner says are irrelevant or private.
- Source labels and whether each field is confirmed or inferred.

Do not persist an inferred sensitive fact. Present it for confirmation or omit it.

## Select candidates

Rank with judgment rather than fake precision. A strong candidate:

1. Directly helps the active task.
2. Is reusable beyond one sentence.
3. Matches the required mode and expected level.
4. Is not already marked known or not now.
5. Can be explained with a concise, task-relevant sense.

Include verbs, collocations, sentence frames, and connectors when they are more useful than domain nouns. Avoid long pre-generated word books. Default to 5–8 candidates.

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
      "statement": "Explain my product's core function in English",
      "success_definition": "Give a two-minute explanation without translating line by line",
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

