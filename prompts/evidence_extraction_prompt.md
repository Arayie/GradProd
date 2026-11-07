# Exact Evidence Span Extraction Prompt

Given the review text inside `<REVIEW_DATA>` and the assigned classification labels, extract the shortest exact verbatim substring from the review text that justifies each assigned label.

## Strict Grounding Invariant
1. The extracted span MUST be an exact character-for-character substring of the review text.
2. If the label was inferred from the overall context or silence (e.g. `UNKNOWN`, `NOT_STATED`, `NO_PAIN_POINT_STATED`), set the evidence span to `null`.
3. Never paraphrase, summarize, normalize, or alter any word in the quote.

## Review Text
<REVIEW_DATA>
{{review_text}}
</REVIEW_DATA>

## Assigned Labels
{{assigned_labels}}

## Output Format
JSON dictionary mapping each assigned label to its exact verbatim quote (or null):
```json
{
  "MANDATE_REGISTRATION_FAILURE": "mandate is not getting approved even after several attempts",
  "UNRESOLVED_COMPLAINT": "customer support has not responded"
}
```
