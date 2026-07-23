---
name: safe-db-api
description: Query the SAFE database of solvent-extraction (extractant) experiment records through its REST API. Use this skill whenever the user wants to look up, filter, sort, count, or aggregate extractant experiment data -- for example records for a given metal (Eu, Am, etc.), extractant, solvent, or acid-concentration range; selected columns; or counts grouped by a field. Also use it whenever the user mentions the SAFE DB, extractant records, distribution/extraction experiments, or the /api/extractants endpoints, or whenever a task needs data pulled from the SAFE REST API rather than a local file.
---

# SAFE DB REST API

The SAFE database exposes solvent-extraction experiment records over a small
read-only REST API. This skill wraps those endpoints so you can answer data
questions by calling the API instead of hand-writing HTTP requests.

Use the bundled client at `scripts/safe_client.py`. For the full field list,
per-endpoint parameters, and response shapes, read `references/fields.md`.

## Setup

The client talks to the public SAFE deployment at <https://safe.lanl.gov>. The
only thing it needs is an API key:

- `SAFE_API_KEY` (**required**) -- the `X-API-Key` value.
- `SAFE_BASE_URL` (optional) -- overrides the default endpoint. Users normally
  leave this unset.

**If `SAFE_API_KEY` is not set**, don't fail silently or guess: tell the user
they need a key, and how to get one --

1. Register an account at <https://safe.lanl.gov> and sign in.
2. On the profile page, use **Generate API Key**. The key is displayed only
   once, so it must be copied immediately.
3. Export it in the shell so this session can see it:
   `export SAFE_API_KEY=...`

Never echo the key back to the user, never write it into a file, and never
include it in a saved script.

## Running it

Run as a CLI (JSON prints to stdout) or import the functions. The four
subcommands map one-to-one to the four endpoints.

```bash
# 1. First 50 records
python scripts/safe_client.py list

# 2. One record by experiment id
python scripts/safe_client.py get 1

# 3. Filtered query -- general form. Every value below is supplied by the
#    user's request; substitute their field names, values, and page size.
python scripts/safe_client.py query \
  --filter <TEXT_FIELD>=<VALUE> \
  --filter <NUMERIC_FIELD>_min=<NUMBER> \
  --filter <NUMERIC_FIELD>_max=<NUMBER> \
  --sort -<FIELD> --per-page <N> \
  --fields <FIELD>,<FIELD>

# 4. Counts grouped by a field
python scripts/safe_client.py aggregate --group-by <FIELD>
```

Worked example only -- do not reuse these values unless the user asked for
them. "Eu records between 0.5 and 2.0 M acid, newest first, 10 per page":

```bash
python scripts/safe_client.py query \
  --filter Metal_Name=Eu \
  --filter Acid_Concentration_M_min=0.5 \
  --filter Acid_Concentration_M_max=2.0 \
  --sort -exp_id --per-page 10 \
  --fields Metal_Name,Extractant_Name
```

Importing instead -- same rule, the arguments come from the request:

```python
from safe_client import query_extractants, aggregate_extractants

query_extractants(
    filters={"<TEXT_FIELD>": "<VALUE>", "<NUMERIC_FIELD>_min": <NUMBER>},
    sort="-<FIELD>",
    per_page=<N>,
    fields=["<FIELD>", "<FIELD>"],
)
aggregate_extractants(group_by="<FIELD>")
```

Pick `<FIELD>` names from `references/fields.md` -- they are the only ones the
API accepts.

## Query rules to know

These matter for building correct filters. Full details in
`references/fields.md`.

- **Exact match**: `Field=value` for any field (e.g. `Metal_Name=Eu`).
- **Numeric ranges**: append `_min` / `_max` to a numeric field
  (e.g. `Acid_Concentration_M_min=0.5`). Range filters only apply to numeric
  fields; using them on a text field is a 400 error.
- **`numeric_multi` caveat**: several concentration/oxidation-state columns
  store multiple `"value unit"` entries per record. Range and equality
  comparisons only look at the **first** entry -- so a range filter may not
  behave as expected on multi-valued records. Mention this if it could affect
  the answer.
- **Sorting**: `--sort Field` ascending, `--sort -Field` descending. Results
  are secondarily ordered by `exp_id` for stable pagination.
- **Pagination**: `--page` (1-based) and `--per-page` (default 50, server caps
  at 500). The `query` response includes `total`, so page through when
  `total` exceeds what you fetched.
- **Field selection**: `--fields A,B,C` returns only those columns; `exp_id`
  is always added automatically.
- **Valid fields only**: unknown field or sort names are rejected with a 400.
  Check `references/fields.md` before inventing a field name.

## Endpoints and tables

- `list` and `get` read the `initialtable` and return whatever columns it has.
- `query` and `aggregate` read the `initialTablePlus` view; the filterable /
  sortable / selectable field names in `references/fields.md` apply to these
  two.

## Errors

The client raises with the server's message attached:

- **401** -- missing, invalid, or revoked key. Re-check `SAFE_API_KEY`.
- **400** -- unknown field, non-numeric value where a number is required, or a
  range where `min > max`. Fix the offending parameter.
- **404** (single record) -- `get` returns `None`; report that no record has
  that `exp_id` rather than treating it as an error.

## Presenting results

Summarize what the user asked for rather than dumping raw JSON, unless they
want the raw payload. For `query`, state the `total` match count alongside the
rows shown so it's clear whether results were truncated by pagination.
