# Data extraction

Turn loosely formatted text (bullet lists, tables pasted as text, semi-structured notes) into clean JSON.

## Rules

- Decide the schema first, state it, then extract. Do not change the schema halfway through.
- Preserve the source's exact strings for identifiers; normalise only whitespace and case where told to.
- Never invent records. If a line does not fit the pattern, list it under `unparsed` rather than guessing.
- Deduplicate entities by exact name after whitespace normalisation.
- Report counts at the end: records found, records skipped.
