---
name: safe-db-api
description: Query the SAFE database of solvent-extraction records through its REST API -- both wet-lab experiment records and computational (simulation) records. Use this skill whenever the user wants to look up, filter, sort, count, or aggregate extractant/ligand data -- for example records for a given metal (Eu, Am, etc.), extractant/ligand, solvent, acid-concentration range, or computational method; a substructure or Tanimoto-similarity chemistry search; selected columns; or counts grouped by a field. Also use it whenever the user mentions the SAFE DB, extractant/ligand records, distribution/extraction experiments, or the /api/experiments or /api/simulations endpoints, or whenever a task needs data pulled from the SAFE REST API rather than a local file.
---

# SAFE DB REST API

The SAFE database exposes solvent-extraction records over a small read-only
REST API, split into two resources: **experiments** (wet-lab records) and
**simulations** (computational records). Both share `exp_id` numbering. This
skill wraps those endpoints so you can answer data questions by calling the
API instead of hand-writing HTTP requests.

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
   once, so it must be copied immediately. At most 3 active keys per user --
   if they're at the limit, revoke one on the same page first.
3. Export it in the shell so this session can see it:
   `export SAFE_API_KEY=...`

Never echo the key back to the user, never write it into a file, and never
include it in a saved script.

## Running it

Run as a CLI (JSON prints to stdout) or import the functions. The CLI takes a
resource first (`experiments` or `simulations`), then one of four
subcommands that map to the four endpoints per resource.

```bash
# 1. First 50 records
python scripts/safe_client.py experiments list
python scripts/safe_client.py simulations list

# 2. One record by experiment id
python scripts/safe_client.py experiments get 1
python scripts/safe_client.py simulations get 1

# 3. Filtered query -- general form. Every value below is supplied by the
#    user's request; substitute their field names, values, and page size.
#    Note the "=" in --sort=-Field: "--sort -Field" (space) breaks argparse.
python scripts/safe_client.py experiments query \
  --filter <TEXT_FIELD>=<VALUE> \
  --filter <NUMERIC_FIELD>_min=<NUMBER> \
  --filter <NUMERIC_FIELD>_max=<NUMBER> \
  --sort=-<FIELD> --per-page <N> \
  --fields <FIELD>,<FIELD>

# 4. Counts grouped by a field
python scripts/safe_client.py experiments aggregate --group-by <FIELD>
```

Worked examples only -- do not reuse these values unless the user asked for
them.

"Eu experiment records between 0.5 and 2.0 M acid, newest first, 10 per page":

```bash
python scripts/safe_client.py experiments query \
  --filter Metal_Name=Eu \
  --filter Acid_Concentration_M_min=0.5 \
  --filter Acid_Concentration_M_max=2.0 \
  --sort=-exp_id --per-page 10 \
  --fields Metal_Name,Extractant_Name
```

"Eu or Am records" (repeat the filter key to OR):

```bash
python scripts/safe_client.py experiments query \
  --filter Metal_Name=Eu --filter Metal_Name=Am
```

"Computational records whose ligand is at least 80% similar to ethanol":

```bash
python scripts/safe_client.py simulations query \
  --similar-to CCO --similarity-min 0.8
```

Importing instead -- same rule, the arguments come from the request:

```python
from safe_client import query_experiments, aggregate_experiments, query_simulations

query_experiments(
    filters={"<TEXT_FIELD>": "<VALUE>", "<NUMERIC_FIELD>_min": <NUMBER>},
    sort="-<FIELD>",
    per_page=<N>,
    fields=["<FIELD>", "<FIELD>"],
)
aggregate_experiments(group_by="<FIELD>")
query_simulations(substructure="c1ccccc1")  # aromatic ring in the ligand
```

Pick `<FIELD>` names from `references/fields.md` -- separate catalogs for
experiments and simulations, they are the only ones the API accepts.

## Query rules to know

These matter for building correct filters. Full details in
`references/fields.md`.

- **Exact match**: `Field=value` for any field (e.g. `Metal_Name=Eu`).
- **OR within a field**: repeat the filter key, e.g. `--filter Metal_Name=Eu
  --filter Metal_Name=Am` matches either. Different fields AND together.
- **Numeric ranges**: append `_min` / `_max` to a numeric field
  (e.g. `Acid_Concentration_M_min=0.5`). Range filters only apply to numeric
  fields; using them on a text field is a 400 error. A field whose own name
  already ends in `_min`/`_max` (`Contact_Time_min`) needs the doubled suffix
  to be range-filtered (`Contact_Time_min_min`).
- **`numeric_multi` / `numeric_unit` caveat**: several concentration/
  oxidation-state/time columns store one or more `"value unit"` entries.
  Range and equality comparisons only look at the **first** entry -- so a
  range filter may not behave as expected on multi-valued records. Mention
  this if it could affect the answer.
- **Missing-value sentinels**: some numeric fields (`Distribution_Ratio`,
  `Temperature`, `Radiolytic_Dose_kGy`, most simulation thermodynamic fields,
  etc.) use a literal `"-"` or `"- -"` for "not measured"; the API already
  excludes those from numeric filters, no client-side handling needed.
- **Chemistry search**: `substructure=<SMARTS/SMILES>` and
  `similar_to=<SMILES>` (+ optional `similarity_min`, default 0.7) filter by
  the extractant (experiments) or ligand (simulations). `similar_to` adds a
  `Tanimoto_Similarity` field to each result row, but results are **not**
  sorted by it -- sort client-side if the user wants them ranked.
- **Sorting**: `--sort=-Field` (use `=`, not a space) for descending,
  `--sort=Field` for ascending. Results are secondarily ordered by `exp_id`
  for stable pagination.
- **Pagination**: `--page` (1-based) and `--per-page` (default 50, server caps
  at 500). The `query` response includes `total`, so page through when
  `total` exceeds what you fetched.
- **Field selection**: `--fields A,B,C` returns only those columns; `exp_id`
  is always added automatically. Simulations' large file columns
  (`Final_Optimized_Structure_file`, etc.) are only returned if named here.
- **Valid fields only**: unknown field, sort, `fields`, or `group_by` names
  are rejected with a 400. Check `references/fields.md` before inventing a
  field name -- experiments and simulations have separate field lists.

## Endpoints and resources

- `experiments list` / `experiments get` read `initialtable` and return
  whatever columns it has.
- `experiments query` / `experiments aggregate` read the `initialTablePlus`
  join (finalTable, provenance, D-values, temperatures, actions, volume
  ratio, third phase); the field names in `references/fields.md` section 4
  apply to these two.
- `simulations list` / `simulations get` / `simulations query` /
  `simulations aggregate` read the simulation views (`view_SimulationComponents`,
  `view_SimulationMethods`, `view_SimulationObs`); field names in
  `references/fields.md` section 5 apply.

## Errors

The client raises with the server's message attached:

- **401** -- missing, invalid, or revoked key. Re-check `SAFE_API_KEY`.
- **400** -- unknown field, non-numeric value where a number is required, a
  range where `min > max`, or an unparseable `substructure`/`similar_to`.
  Fix the offending parameter.
- **404** (single record) -- `get` returns `None`; report that no record has
  that `exp_id` rather than treating it as an error.
  
## When a request fails

Always use `scripts/safe_client.py`. Never construct API URLs by hand or probe
endpoints directly — the client is the only supported interface, and guessed
paths (`/api/experiments/list`, `/api/extractants`) do not exist.

If the client reports a connection error or 404 on the base URL, the API is
not reachable at `SAFE_BASE_URL` (or its default). Report that to the user and
ask them to confirm the endpoint. Do not try alternative paths.

An empty `results` list with `total: 0` is a valid answer, not an error — it
means nothing matched.

## Presenting results

Summarize what the user asked for rather than dumping raw JSON, unless they
want the raw payload. For `query`, state the `total` match count alongside the
rows shown so it's clear whether results were truncated by pagination. If a
`similar_to` search was used, note that ranking by `Tanimoto_Similarity` (if
relevant) was done client-side, not by the server.
