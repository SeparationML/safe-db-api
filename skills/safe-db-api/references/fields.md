# SAFE DB REST API -- reference

Read this when you need exact endpoint parameters, the full list of queryable
fields, or the precise query semantics.

## Contents

1. Authentication
2. Experimental vs. computational records
3. Endpoints
4. Field catalog -- experiments (`query` / `aggregate`)
5. Field catalog -- simulations (`query` / `aggregate`)
6. Chemistry filters (`substructure`, `similar_to`, `similarity_min`)
7. Query parameter semantics
8. Response shapes
9. Error responses

---

## 1. Authentication

Every endpoint requires the header `X-API-Key: <key>`. The client sends this
automatically from `SAFE_API_KEY`. Keys require a registered account at
<https://safe.lanl.gov> and are issued on the profile page (`Generate API
Key`, shown once); they can be revoked from the same page. **At most 3 active
keys per user** -- revoke one before generating another if you hit the limit.
A missing, unknown, or revoked key returns `401`.

---

## 2. Experimental vs. computational records

The database holds two disjoint record types, both keyed by `exp_id`:

- **experiments** -- wet-lab records (6,677 as of writing). Endpoints under
  `/api/experiments/...`.
- **simulations** -- computational records (593 as of writing). Endpoints
  under `/api/simulations/...`.

Since both use the same `exp_id` numbering, look up the same `exp_id` on the
other resource to cross-reference a computational record with an experimental
one for the same study, if one exists.

---

## 3. Endpoints

All are `GET`, against the public deployment at `https://safe.lanl.gov`
(overridable via `SAFE_BASE_URL`).

| Endpoint | Purpose |
| --- | --- |
| `/api/experiments` | First 50 experiment records |
| `/api/experiments/<exp_id>` | One experiment record by id |
| `/api/experiments/query` | Filtered / sorted / paginated experiment query |
| `/api/experiments/aggregate` | Grouped experiment counts |
| `/api/simulations` | First 50 computational records (large file columns omitted) |
| `/api/simulations/<exp_id>` | One computational record by id, including its structure/vibration files |
| `/api/simulations/query` | Filtered / sorted / paginated computational query |
| `/api/simulations/aggregate` | Grouped computational-record counts |

Notes:

- `/api/experiments` and `/api/simulations` are a fixed 50-row sample with no
  parameters -- use `query` for anything filtered or paginated.
- `/api/experiments/<exp_id>` and `/api/simulations/<exp_id>` return `404`
  when no record matches.
- The field catalogs in sections 4 and 5 apply to `query` and `aggregate` for
  their respective resource.
- `/api/experiments` and `/api/experiments/<exp_id>` read `initialtable`
  directly and return a concatenated summary format -- their column names are
  **not** the section 4 field names and cannot be used as filters.
  `/api/simulations` and `/api/simulations/<exp_id>` do use the section 5
  field names.

---

## 4. Field catalog -- experiments (`query` / `aggregate`)

Type determines how a field can be filtered:

- **text** -- exact match only (`Field=value`).
- **numeric** -- exact match and range (`Field_min` / `Field_max`).
- **numeric_multi** -- same operators as numeric, **but** the column stores
  one or more comma-separated `"value unit"` entries (e.g. `"0.5 M,0.2 M"`),
  and every comparison uses only the **first** entry. Treat range results on
  multi-valued records with caution.
- **numeric_unit** -- a single `"value unit"` entry (e.g. `"2.0 min"`), no
  comma list; comparisons parse the leading number.

Some numeric fields also use a **literal sentinel** ("missing") such as `"-"`
or `"- -"` to mean "not measured" rather than SQL `NULL`. The API excludes
sentinel values from range/equality comparisons automatically (a naive
numeric cast would otherwise silently read `"-"` as `0`).

| Field | Type | Range-filterable | Notes |
| --- | --- | --- | --- |
| `exp_id` | numeric | yes | Experiment id (primary key). Always included in `query` output and used as the tiebreaker sort. |
| `Extractant_Name` | text | no | |
| `Extractant_Concentration_M` | numeric_multi | yes | First entry only |
| `Acid_Name` | text | no | |
| `Acid_Concentration_M` | numeric_multi | yes | First entry only |
| `Solvent_Name` | text | no | |
| `Metal_Name` | text | no | e.g. `Eu`, `Am` |
| `Metal_Oxidation_state` | numeric_multi | yes | First entry only |
| `Metal_Concentration_mM` | numeric_multi | yes | First entry only |
| `Phase_Modifier_Name` | text | no | |
| `Phase_Modifier_Concentration_M` | numeric_multi | yes | First entry only |
| `Holdback_Agent_Name` | text | no | |
| `Holdback_Agent_Concentration_M` | numeric_multi | yes | First entry only |
| `Inorganic_Salt` | text | no | |
| `Inorganic_Salt_Concentration_M` | numeric_multi | yes | First entry only |
| `Oxidizing_Reducing_Agent` | text | no | |
| `Oxidizing_Reducing_Agent_Concentration_M` | numeric_multi | yes | First entry only |
| `Extractant_SMILES` | text | no | |
| `Extractant_inchi` | text | no | |
| `Distribution_Ratio` | numeric | yes | Missing sentinel `"-"`. Usually one decimal, rarely a multi-reading string -- filtering still lands on the first reading |
| `Temperature` | numeric | yes | Missing sentinel `"-"` |
| `Volume_Ratio` | numeric | yes | Missing sentinel `"-"` |
| `Radiolytic_Dose_kGy` | numeric_unit | yes | Missing sentinel `"- -"` |
| `Contact_Time_min` | numeric_unit | yes | Missing sentinel `"- -"`. **Note:** this field name itself ends in `_min` -- see section 7 for how that's disambiguated from a range bound |
| `Third_Phase` | text | no | |
| `DOI` | text | no | |
| `Addition_Date` | text | no | |

Returned by default but **not** filterable/sortable (internal identifiers,
not real filter values): `initial_phase_id`, `ini_comp`.

Any field name outside the table above and this extra pair -- as a filter,
sort, `fields` entry, or `group_by` -- is rejected with `400`.

---

## 5. Field catalog -- simulations (`query` / `aggregate`)

Same type rules as section 4.

| Field | Type | Range-filterable | Notes |
| --- | --- | --- | --- |
| `exp_id` | numeric | yes | Shared with experiment records |
| `Ligand` | text | no | |
| `Metal` | text | no | |
| `SMILES` | text | no | |
| `Metal_Oxidation_state` | numeric | yes | Missing sentinel `"-"` |
| `Method` | text | no | |
| `Software` | text | no | |
| `Total_Charge` | numeric | yes | Missing sentinel `"-"` |
| `Total_Spin` | numeric | yes | Missing sentinel `"-"` |
| `Electronic_Energy` | numeric | yes | Missing sentinel `"-"` |
| `Gibbs_Free_Energy` | numeric | yes | Missing sentinel `"-"`. Empty for every record as of writing -- database still being populated |
| `Enthalpy` | numeric | yes | Missing sentinel `"-"`. Empty for every record as of writing |
| `Entropy` | numeric | yes | Missing sentinel `"-"`. Empty for every record as of writing |
| `Solvation_Energy` | numeric | yes | Missing sentinel `"-"`. Empty for every record as of writing |

Returned by default but **not** filterable/sortable:
`property_metal1`, `property_metal2`, `concentration`, `method_properties`,
`Solvation_Parameters`. (`property_metal2`, "Unpaired Electrons: N", is
otherwise unavailable as a named field -- it duplicates `Total_Spin`.)

**Excluded from the default response** (large columns) but selectable by
name via `fields=`, and always included on `/api/simulations/<exp_id>`:
`Final_Optimized_Structure_file` (~5,500 characters of XYZ coordinates per
row), `Final_Mulliken_Charges_Spin_Densities_file`,
`Final_Vibrational_Modes_file`.

Any field name outside these three groups is rejected with `400`.

---

## 6. Chemistry filters (`substructure`, `similar_to`, `similarity_min`)

Available on `/api/experiments/query` and `/api/simulations/query` only (not
`aggregate`). Combine with any other filter -- ANDed together like two field
filters.

- `substructure=<SMARTS or SMILES>` -- matches records whose extractant
  (experiments) or ligand (simulations) contains this substructure. Parsed as
  SMARTS first, falling back to SMILES; an unparseable pattern returns `400`.
- `similar_to=<SMILES>` with `similarity_min=<0.0-1.0, default 0.7>` --
  matches records whose extractant/ligand has Tanimoto similarity to this
  molecule at or above the threshold. An unparseable SMILES, or a
  `similarity_min` outside `0-1` (or given without `similar_to`), returns
  `400`.

When `similar_to` matches, each result row gets a `Tanimoto_Similarity` field
(the highest score among that record's matching extractants/ligands).
**Results are not sorted by this score** -- ordering happens in SQL before
the chemistry match runs in Python, and sorting by a Python-computed value
would break `total`/pagination. Sort by `Tanimoto_Similarity` client-side if
you need it ranked.

Similarity uses Morgan fingerprints (radius 2, 2048 bits), computed once per
process for the database's ~73 distinct SMILES and cached in memory: a
molecule added after the server started won't be matchable until the process
restarts.

---

## 7. Query parameter semantics

Reserved parameters (not treated as field filters): `sort`, `page`,
`per_page`, `fields`, `group_by`, `substructure`, `similar_to`,
`similarity_min`. Everything else in the query string is read as a filter.

**Filters**

- Exact match: `Field=value`. For numeric / numeric_multi / numeric_unit
  fields the value must parse as a number.
- **Repeat a key to OR within that field**: `Metal_Name=Eu&Metal_Name=Am`
  matches `Metal_Name IN ('Eu', 'Am')`. Different fields are ANDed, e.g.
  `?Metal_Name=Eu&Metal_Name=Am&Acid_Name=HNO3` matches
  `Metal_Name IN ('Eu', 'Am') AND Acid_Name = 'HNO3'`.
- Range: `Field_min=<number>` and/or `Field_max=<number>`, numeric fields
  only. Both bounds are inclusive. `min > max` is a `400`. Range params must
  not be repeated. A field name that itself ends in `_min`/`_max` (currently
  only `Contact_Time_min`) is matched as its own literal name first --
  range-filtering it needs the doubled suffix (`Contact_Time_min_min`,
  `Contact_Time_min_max`).

**`sort`** -- one field name; leading `-` means descending. Output is always
ordered by that field then by `exp_id`, so pagination is stable across pages.
CLI/shell note: pass it as `--sort=-Field` (with `=`) -- `--sort -Field` makes
most shells/argparse treat `-Field` as a new flag.

**`page` / `per_page`** -- `page` is 1-based; both must be positive integers.
`per_page` defaults to 50 and is capped at 500. Use the `total` in the
response to decide how many pages exist.

**`fields`** -- comma-separated column list, restricting the columns returned
by `query`. `exp_id` is appended automatically if omitted. (No effect on
`aggregate`.)

**`group_by`** (`aggregate` only, required) -- one field to group by; filters
apply before grouping.

---

## 8. Response shapes

`/api/experiments` / `/api/simulations` -> JSON array of record objects (up
to 50).

`/api/experiments/<exp_id>` / `/api/simulations/<exp_id>` -> a single record
object, or `{"error": "Not found"}` with status `404`.

`/api/experiments/query` / `/api/simulations/query`:

```json
{
  "total": 123,
  "page": 1,
  "per_page": 50,
  "results": [ { "exp_id": 1, "Metal_Name": "...", "...": "..." } ]
}
```

`total` is the full match count before pagination; `results` is the current
page. Rows carry a `Tanimoto_Similarity` field too when `similar_to` was
given (see section 6). Values joined with `-,-` internally (multi-reading
columns) are cleaned to a plain comma before being returned.

`/api/experiments/aggregate` / `/api/simulations/aggregate`:

```json
{
  "groups": [
    { "group": "Eu", "count": 42 },
    { "group": "Am", "count": 17 }
  ]
}
```

`group` holds each distinct value of the `group_by` field.

---

## 9. Error responses

| Status | When | Body |
| --- | --- | --- |
| 400 | Unknown field / sort / group_by / `fields` entry; non-numeric value where a number is required; range on a non-numeric field; `min > max`; bad `page`/`per_page`; unparseable `substructure`; unparseable `similar_to`; `similarity_min` outside `0-1` or given without `similar_to` | `{"error": "<reason>"}` |
| 401 | Missing, invalid, or revoked API key | `{"error": "Missing API key"}` or `{"error": "Invalid or revoked API key"}` |
| 404 | Single record not found | `{"error": "Not found"}` |

The client attaches the `error` message to the exception it raises, so
surface that text when reporting a failure.
