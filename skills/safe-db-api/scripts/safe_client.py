"""
Client for the SAFE DB REST API.

Auth and endpoint are read from the environment so no secrets live in this
file:

    SAFE_API_KEY   (required)  the X-API-Key value. Register at
                               https://safe.lanl.gov and generate a key on the
                               profile page (it is shown only once).
    SAFE_BASE_URL  (optional)  overrides the endpoint; defaults to the public
                               deployment at https://safe.lanl.gov

Two ways to use it:

  * Import the functions (list_extractants, get_extractant,
    query_extractants, aggregate_extractants) into your own Python.
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


def list_extractants():
    """First 50 rows from /api/extractants (table: initialtable)."""
    return _get("/api/extractants")


def get_extractant(exp_id):
    """A single record by experiment id. Returns None if not found (404)."""
    resp = requests.get(
        f"{_base_url()}/api/extractants/{exp_id}", headers=_headers()
    )
    if resp.status_code == 404:
        return None
    _raise_for_status(resp)
    return resp.json()


def query_extractants(
    filters=None, sort=None, page=1, per_page=50, fields=None
):
    """
    Filtered query against /api/extractants/query (table: initialTablePlus).

    filters : dict of API query params, using the exact field names.
              * exact match:  {"Metal_Name": "Eu"}
              * numeric range: append "_min"/"_max" to a numeric field, e.g.
                {"Acid_Concentration_M_min": 0.5, "Acid_Concentration_M_max": 2.0}
    sort     : field name; prefix "-" for descending, e.g. "-exp_id".
    page     : 1-based page number.
    per_page : rows per page (server caps at 500; default 50).
    fields   : list of columns to return; exp_id is always included, e.g.
               ["Metal_Name", "Extractant_Name"].

    Returns {"total", "page", "per_page", "results"}.
    """
    params = dict(filters or {})
    if sort:
        params["sort"] = sort
    if fields:
        params["fields"] = ",".join(fields)
    params["page"] = page
    params["per_page"] = per_page
    return _get("/api/extractants/query", params)


def aggregate_extractants(group_by, filters=None):
    """
    Count of records grouped by a field, via /api/extractants/aggregate
    (table: initialTablePlus). `filters` follows query_extractants' shape.
    Returns {"groups": [{"group": ..., "count": ...}, ...]}.
    """
    params = dict(filters or {})
    params["group_by"] = group_by
    return _get("/api/extractants/aggregate", params)


# --- CLI ---------------------------------------------------------------------


def _split_pairs(pairs):
    """Turn ["Metal_Name=Eu", "Acid_Concentration_M_min=0.5"] into a dict."""
    out = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"--filter expects KEY=VALUE, got: {item!r}")
        key, value = item.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _emit(data):
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _build_parser():
    p = argparse.ArgumentParser(
        description="Query the SAFE DB REST API. Output is JSON on stdout."
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="First 50 rows (GET /api/extractants).")

    g = sub.add_parser("get", help="Single record by exp_id.")
    g.add_argument("exp_id", type=int)

    q = sub.add_parser("query", help="Filtered query (GET /api/extractants/query).")
    q.add_argument(
        "--filter", action="append", metavar="KEY=VALUE",
        help="Repeatable. Use exact API param names, incl. _min/_max, e.g. "
             "--filter Metal_Name=Eu --filter Acid_Concentration_M_min=0.5",
    )
    q.add_argument("--sort", help='Field name; prefix "-" for descending.')
    q.add_argument("--page", type=int, default=1)
    q.add_argument("--per-page", type=int, default=50, dest="per_page")
    q.add_argument("--fields", help="Comma-separated columns to return.")

    a = sub.add_parser("aggregate", help="Grouped counts (GET /api/extractants/aggregate).")
    a.add_argument("--group-by", required=True, dest="group_by")
    a.add_argument(
        "--filter", action="append", metavar="KEY=VALUE",
        help="Repeatable; same shape as query --filter.",
    )
    return p


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "list":
            _emit(list_extractants())
        elif args.command == "get":
            result = get_extractant(args.exp_id)
            if result is None:
                print(f"No record with exp_id={args.exp_id}", file=sys.stderr)
                return 1
            _emit(result)
        elif args.command == "query":
            fields = args.fields.split(",") if args.fields else None
            _emit(query_extractants(
                filters=_split_pairs(args.filter),
                sort=args.sort,
                page=args.page,
                per_page=args.per_page,
                fields=fields,
            ))
        elif args.command == "aggregate":
            _emit(aggregate_extractants(
                group_by=args.group_by,
                filters=_split_pairs(args.filter),
            ))
    except (RuntimeError, ValueError, requests.HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
