"""
Client for the SAFE DB REST API.

Auth and endpoint are read from the environment so no secrets live in this
file:

    SAFE_API_KEY   (required)  the X-API-Key value. Register at
                               https://safe.lanl.gov and generate a key on the
                               profile page (it is shown only once). At most 3
                               active keys per user; revoke one to make room.
    SAFE_BASE_URL  (optional)  overrides the endpoint; defaults to the public
                               deployment at https://safe.lanl.gov

Two resource types, same shape of four endpoints each:

  * experiments  -- wet-lab records (6,677 as of writing)
  * simulations  -- computational records (593 as of writing)

Both share exp_id numbering, so exp_id cross-references a computational
record with an experimental one for the same study, if one exists.

Two ways to use it:

  * Import the functions (list_experiments, get_experiment,
    query_experiments, aggregate_experiments, and the simulations
    equivalents) into your own Python.
  * Run it as a CLI and read JSON from stdout (see `python safe_client.py -h`).

All endpoints require a valid API key; requests without SAFE_API_KEY set will
fail fast with a clear message.
"""

import argparse
import json
import os
import sys

import requests

# Public SAFE deployment. Overridable at runtime via SAFE_BASE_URL.
DEFAULT_BASE_URL = "https://safe.lanl.gov"


def _base_url():
    return os.environ.get("SAFE_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _headers():
    key = os.environ.get("SAFE_API_KEY")
    if not key:
        raise RuntimeError(
            "SAFE_API_KEY is not set. Register at https://safe.lanl.gov and "
            "generate a key on your profile page (it is shown only once), "
            "then export it:  export SAFE_API_KEY=your-key-here"
        )
    return {"X-API-Key": key}


def _raise_for_status(resp):
    """Raise with the server's JSON error message attached, if there is one."""
    if resp.ok:
        return
    detail = ""
    try:
        body = resp.json()
        detail = body.get("error", "") if isinstance(body, dict) else str(body)
    except ValueError:
        detail = resp.text.strip()
    msg = f"{resp.status_code} {resp.reason} for {resp.url}"
    if detail:
        msg += f" -- {detail}"
    raise requests.HTTPError(msg, response=resp)


def _get(path, params=None):
    """GET `path` and return parsed JSON. Raises on HTTP errors."""
    resp = requests.get(f"{_base_url()}{path}", headers=_headers(), params=params)
    _raise_for_status(resp)
    return resp.json()


def _get_by_id(resource, record_id):
    """GET `/api/<resource>/<record_id>`. Returns None on 404."""
    resp = requests.get(
        f"{_base_url()}/api/{resource}/{record_id}", headers=_headers()
    )
    if resp.status_code == 404:
        return None
    _raise_for_status(resp)
    return resp.json()


def _query(resource, filters, sort, page, per_page, fields,
           substructure, similar_to, similarity_min):
    """
    Shared implementation for query_experiments/query_simulations --
    the two endpoints take identical parameters.

    filters : dict of API query params, using the exact field names (see
              references/fields.md). Pass a list as a value to OR within
              that field, e.g. {"Metal_Name": ["Eu", "Am"]}.
              * exact match:  {"Metal_Name": "Eu"}
              * numeric range: append "_min"/"_max" to a numeric field, e.g.
                {"Acid_Concentration_M_min": 0.5, "Acid_Concentration_M_max": 2.0}
    sort     : field name; prefix "-" for descending, e.g. "-exp_id".
    page     : 1-based page number.
    per_page : rows per page (server caps at 500; default 50).
    fields   : list of columns to return; exp_id is always included.
    substructure  : SMARTS or SMILES the extractant/ligand must contain.
    similar_to    : SMILES to Tanimoto-match the extractant/ligand against.
    similarity_min: threshold 0.0-1.0 (default 0.7 server-side); requires
                    similar_to.

    Returns {"total", "page", "per_page", "results"}. When similar_to
    matches, each row in "results" also carries "Tanimoto_Similarity" --
    NOT reflected in "sort" (see references/fields.md); sort client-side
    if you need results ranked by it.
    """
    params = dict(filters or {})
    if sort:
        params["sort"] = sort
    if fields:
        params["fields"] = ",".join(fields)
    if substructure:
        params["substructure"] = substructure
    if similar_to:
        params["similar_to"] = similar_to
    if similarity_min is not None:
        params["similarity_min"] = similarity_min
    params["page"] = page
    params["per_page"] = per_page
    return _get(f"/api/{resource}/query", params)


def _aggregate(resource, group_by, filters):
    params = dict(filters or {})
    params["group_by"] = group_by
    return _get(f"/api/{resource}/aggregate", params)


# --- Experiments (wet-lab records, exp_type = 0) ------------------------------


def list_experiments():
    """First 50 rows from /api/experiments (table: initialtable)."""
    return _get("/api/experiments")


def get_experiment(exp_id):
    """A single experiment record by exp_id. Returns None if not found (404)."""
    return _get_by_id("experiments", exp_id)


def query_experiments(filters=None, sort=None, page=1, per_page=50, fields=None,
                       substructure=None, similar_to=None, similarity_min=None):
    """Filtered query against /api/experiments/query. See `_query` for params."""
    return _query("experiments", filters, sort, page, per_page, fields,
                  substructure, similar_to, similarity_min)


def aggregate_experiments(group_by, filters=None):
    """
    Count of experiment records grouped by a field, via
    /api/experiments/aggregate. Returns {"groups": [{"group": ..., "count": ...}]}.
    """
    return _aggregate("experiments", group_by, filters)


# --- Simulations (computational records, exp_type = 1) -----------------------


def list_simulations():
    """First 50 rows from /api/simulations. Large structure/vibration-file
    columns are omitted by default (request them via `fields=` on query)."""
    return _get("/api/simulations")


def get_simulation(exp_id):
    """A single computational record by exp_id, including its structure and
    vibrational-mode files. Returns None if not found (404)."""
    return _get_by_id("simulations", exp_id)


def query_simulations(filters=None, sort=None, page=1, per_page=50, fields=None,
                       substructure=None, similar_to=None, similarity_min=None):
    """Filtered query against /api/simulations/query. See `_query` for params."""
    return _query("simulations", filters, sort, page, per_page, fields,
                  substructure, similar_to, similarity_min)


def aggregate_simulations(group_by, filters=None):
    """
    Count of computational records grouped by a field, via
    /api/simulations/aggregate. Returns {"groups": [{"group": ..., "count": ...}]}.
    """
    return _aggregate("simulations", group_by, filters)


# --- CLI ---------------------------------------------------------------------


def _split_pairs(pairs):
    """Turn ["Metal_Name=Eu", "Metal_Name=Am"] into {"Metal_Name": ["Eu", "Am"]}
    (repeated keys OR together, matching the API's semantics), single
    occurrences into a plain string value."""
    out = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"--filter expects KEY=VALUE, got: {item!r}")
        key, value = item.split("=", 1)
        key, value = key.strip(), value.strip()
        if key in out:
            if isinstance(out[key], list):
                out[key].append(value)
            else:
                out[key] = [out[key], value]
        else:
            out[key] = value
    return out


def _emit(data):
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _add_query_args(sub_parser):
    sub_parser.add_argument(
        "--filter", action="append", metavar="KEY=VALUE",
        help="Repeatable. Use exact API param names, incl. _min/_max. Repeat "
             "the same key to OR within that field, e.g. "
             "--filter Metal_Name=Eu --filter Metal_Name=Am",
    )
    sub_parser.add_argument("--sort", help='Field name; prefix "-" for descending.')
    sub_parser.add_argument("--page", type=int, default=1)
    sub_parser.add_argument("--per-page", type=int, default=50, dest="per_page")
    sub_parser.add_argument("--fields", help="Comma-separated columns to return.")
    sub_parser.add_argument(
        "--substructure", help="SMARTS or SMILES the extractant/ligand must contain."
    )
    sub_parser.add_argument(
        "--similar-to", dest="similar_to",
        help="SMILES to Tanimoto-match the extractant/ligand against.",
    )
    sub_parser.add_argument(
        "--similarity-min", dest="similarity_min", type=float,
        help="Threshold 0.0-1.0 (default 0.7 server-side); requires --similar-to.",
    )


def _build_parser():
    p = argparse.ArgumentParser(
        description="Query the SAFE DB REST API. Output is JSON on stdout."
    )
    resource_sub = p.add_subparsers(dest="resource", required=True)

    for resource in ("experiments", "simulations"):
        rp = resource_sub.add_parser(resource, help=f"{resource} endpoints")
        action_sub = rp.add_subparsers(dest="command", required=True)

        action_sub.add_parser("list", help=f"First 50 rows (GET /api/{resource}).")

        g = action_sub.add_parser("get", help="Single record by exp_id.")
        g.add_argument("exp_id", type=int)

        q = action_sub.add_parser(
            "query", help=f"Filtered query (GET /api/{resource}/query)."
        )
        _add_query_args(q)

        a = action_sub.add_parser(
            "aggregate", help=f"Grouped counts (GET /api/{resource}/aggregate)."
        )
        a.add_argument("--group-by", required=True, dest="group_by")
        a.add_argument(
            "--filter", action="append", metavar="KEY=VALUE",
            help="Repeatable; same shape as query --filter.",
        )

    return p


def main(argv=None):
    args = _build_parser().parse_args(argv)
    list_fn, get_fn, query_fn, aggregate_fn = {
        "experiments": (list_experiments, get_experiment, query_experiments, aggregate_experiments),
        "simulations": (list_simulations, get_simulation, query_simulations, aggregate_simulations),
    }[args.resource]

    try:
        if args.command == "list":
            _emit(list_fn())
        elif args.command == "get":
            result = get_fn(args.exp_id)
            if result is None:
                print(f"No record with exp_id={args.exp_id}", file=sys.stderr)
                return 1
            _emit(result)
        elif args.command == "query":
            fields = args.fields.split(",") if args.fields else None
            _emit(query_fn(
                filters=_split_pairs(args.filter),
                sort=args.sort,
                page=args.page,
                per_page=args.per_page,
                fields=fields,
                substructure=args.substructure,
                similar_to=args.similar_to,
                similarity_min=args.similarity_min,
            ))
        elif args.command == "aggregate":
            _emit(aggregate_fn(
                group_by=args.group_by,
                filters=_split_pairs(args.filter),
            ))
    except (RuntimeError, ValueError, requests.HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
