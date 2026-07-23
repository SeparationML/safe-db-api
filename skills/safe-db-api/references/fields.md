# SAFE DB REST API -- reference

Read this when you need exact endpoint parameters, the full list of queryable
fields, or the precise query semantics.

## Contents

1. Authentication
2. Endpoints
3. Field catalog (for `query` and `aggregate`)
4. Query parameter semantics
5. Response shapes
6. Error responses

---

## 1. Authentication

Every endpoint requires the header `X-API-Key: <key>`. The client sends this
automatically from `SAFE_API_KEY`. Keys require a registered account at
<https://safe.lanl.gov> and are issued on the profile page (`Generate API Key`,
shown once); they can be revoked from the same page. A missing, unknown, or
revoked key returns `401`.

---

## 2. Endpoints

All are `GET`, against the public deployment at `https://safe.lanl.gov`
(overridable via `SAFE_BASE_URL`).

| Endpoint | Purpose | Table |
| --- | --- | --- |
| `/api/extractants` | First 50 records | `initialtable` |
| `/api/extractants/<exp_id>` | One record by id | `initialtable` |
| `/api/extractants/query` | Filtered / sorted / paginated query | `initialTablePlus` |
| `/api/extractants/aggregate` | Grouped record counts | `initialTablePlus` |

Notes:

- `/api/extractants` is a fixed 50-row sample with no parameters -- use `query`
  for anything filtered or paginated.
- `/api/extractants/<exp_id>` returns `404` when no record matches.
- The queryable field names in section 3 apply to `query` and `aggregate`
  (the `initialTablePlus` view). The two `initialtable` endpoints return
  whatever columns that table has.

---

## 3. Field catalog (for `query` and `aggregate`)

Type determines how a field can be filtered:

- **text** -- exact match only (`Field=value`).
- **numeric** -- exact match and range (`Field_min` / `Field_max`).
- **numeric_multi** -- same operators as numeric, **but** the column stores one
  or more `"value unit"` entries joined together (e.g. `"0.5 M,0.2 M"`), and
  every comparison uses only the **first** entry. Treat range results on
  multi-valued records with caution.

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
| `initial_phase_id` | numeric | yes | |
| `ini_comp` | text | no | |

Any field name outside this list -- as a filter, sort, `fields` entry, or
`group_by` -- is rejected with `400`.

---

## 4. Query parameter semantics

Reserved parameters (not treated as filters): `sort`, `page`, `per_page`,
`fields`, `group_by`. Everything else in the query string is read as a filter.

**Filters**

- Exact match: `Field=value`. For numeric / numeric_multi fields the value must
  parse as a number.
- Range: `Field_min=<number>` and/or `Field_max=<number>`, numeric fields only.
  Both bounds are inclusive. `min > max` is a `400`.
- Multiple filters combine with AND.

**`sort`** -- one field name; leading `-` means descending. Output is always
ordered by that field then by `exp_id`, so pagination is stable across pages.

**`page` / `per_page`** -- `page` is 1-based; both must be positive integers.
`per_page` defaults to 50 and is capped at 500. Use the `total` in the response
to decide how many pages exist.

**`fields`** -- comma-separated column list, restricting the columns returned by
`query`. `exp_id` is appended automatically if omitted. (No effect on
`aggregate`.)

**`group_by`** (`aggregate` only, required) -- one field to group by; filters
apply before grouping.

---

## 5. Response shapes

`/api/extractants` -> JSON array of record objects (up to 50).

`/api/extractants/<exp_id>` -> a single record object, or `{"error": "Not found"}`
with status `404`.

`/api/extractants/query`:

```json
{
  "total": 123,
  "page": 1,
  "per_page": 50,
  "results": [ { "exp_id": 1, "Metal_Name": "...", "...": "..." } ]
}
```

`total` is the full match count before pagination; `results` is the current
page.

`/api/extractants/aggregate`:

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

## 6. Error responses

| Status | When | Body |
| --- | --- | --- |
| 400 | Unknown field / sort / group_by; non-numeric value where a number is required; range on a text field; `min > max`; bad `page`/`per_page` | `{"error": "<reason>"}` |
| 401 | Missing, invalid, or revoked API key | `{"error": "Missing API key"}` or `{"error": "Invalid or revoked API key"}` |
| 404 | Single record not found | `{"error": "Not found"}` |

The client attaches the `error` message to the exception it raises, so surface
that text when reporting a failure.
