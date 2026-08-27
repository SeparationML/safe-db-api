# safe-db-api

An agent skill for querying the **SAFE (Separation Archive for Elements)**
database — a publicly accessible archive of experimental and computational data
on separation processes, including liquid–liquid extraction and solid–liquid
chromatography. Works in both Claude Code and OpenAI Codex.

Install it once, then ask questions in plain language. The agent translates
them into SAFE REST API calls and answers from the returned records — no
commands to memorize, no HTTP requests to hand-write.

> How many europium records are in SAFE?
>
> Which extractants show up most often in nitric acid systems?
>
> List Am records with acid concentration between 0.5 and 2 M, newest first.

Database: <https://safe.lanl.gov>

## Supported environment

This skill supports:

- **Claude Code**, as a Claude Code plugin
- **OpenAI Codex**, as a Codex plugin

Both consume the same skill files under `skills/safe-db-api/` — there is no
platform-specific copy of the query logic.

## Requirements

- A SAFE account and API key (free — see [Get an API key](#get-an-api-key))
- Python 3.8+ with `requests` (`pip install requests`)

## Get an API key

Every endpoint requires a key, and keys are tied to a registered account. This
setup is identical for Claude Code and Codex — the key is a plain environment
variable, not something either plugin manifest handles.

1. Go to <https://safe.lanl.gov> and register an account.
2. Sign in and open your **profile page**.
3. Click **Generate API Key**. The key is shown **only once** — copy it right
   away. You can revoke and regenerate it from the same page.

Then make the key available in the environment where the skill runs:

```bash
export SAFE_API_KEY=your-key-here
```

Add that line to your shell profile (`~/.zshrc`, `~/.bashrc`) to persist it
across sessions.

Never commit a key to a repository or share it in a public issue.

## Install

### Claude Code

The repository is also a Claude Code plugin marketplace, so it installs in two
commands:

```shell
/plugin marketplace add SeparationML/safe-db-api
/plugin install safe-db-api@safe-db
/reload-plugins
```

After installing, start a new conversation and just ask your question — Claude
loads the skill automatically when a request matches it. You never need to run
the client yourself.

### OpenAI Codex

The same repository is also a Codex plugin marketplace:

```bash
codex plugin marketplace add SeparationML/safe-db-api
codex plugin add safe-db-api@safe-db
```

Verify it installed with:

```bash
codex plugin list
```

or open the `/plugins` browser inside the Codex CLI. After installing, just
ask your question in a Codex session — the skill loads automatically when a
request matches it, same as in Claude Code.

## What you can ask

The database covers metals, extractants, acids, solvents, phase modifiers,
holdback agents, inorganic salts, and redox agents, with SMILES and InChI
identifiers for extractants. Claude can:

- **Look up** a single experiment by its `exp_id`
- **Filter** on any field — exact matches for text, `min`/`max` ranges for
  numeric fields like acid or extractant concentration
- **Sort** ascending or descending, and page through large result sets
- **Select columns** so results stay readable
- **Count** records grouped by a field (per metal, per extractant, and so on)
- **Search by structure** substructure (SMARTS/SMILES) or Tanimoto similarity to a query molecule
- **Look up computational records** method, software, energies, oxidation state

Ask for the raw JSON if you want it; otherwise Claude summarizes and reports how
many records matched in total.

## Repository layout

```
.
├── .claude-plugin/
│   ├── marketplace.json    # Claude Code marketplace catalog
│   └── plugin.json         # Claude Code plugin manifest
├── .codex-plugin/
│   └── plugin.json         # Codex plugin manifest
├── .agents/
│   └── plugins/
│       └── marketplace.json   # Codex marketplace catalog
├── skills/
│   └── safe-db-api/
│       ├── SKILL.md        # Instructions the model loads
│       ├── scripts/
│       │   └── safe_client.py   # REST client used by the skill
│       └── references/
│           └── fields.md   # Endpoint spec, field catalog, error contract
└── README.md
```

Both plugin manifests point at the same `skills/safe-db-api/` directory —
there is one implementation, not one per platform. `SKILL.md` and
`references/fields.md` are written for the model, not for end users.
`fields.md` is the API specification the skill consults for valid field names
and query semantics — it is not user documentation.

## Advanced

`scripts/safe_client.py` also works standalone if you want to script against the
API directly:

```bash
python skills/safe-db-api/scripts/safe_client.py experiments aggregate --group-by Metal_Name
```

Run it with `-h` for the full CLI, or import `list_experiments`,
`get_experiment`, `query_experiments`, `aggregate_experiments`, and the
`*_simulations` equivalents from it.

`SAFE_BASE_URL` overrides the API endpoint (default `https://safe.lanl.gov`);
most users never need to set it.

## Contributing to SAFE

SAFE is built by the community. Researchers are invited to contribute
experimental or computational data, with contributions and associated
publications credited. Questions and submissions: **safedb@lanl.gov**.

Issues with *this skill* belong in this repository's issue tracker; questions
about the *data* belong with the SAFE team.

## Maintaining the skill

The API surface is defined by the SAFE Flask application. When endpoints,
columns, or query behavior change, update `references/fields.md` to match —
Claude relies on it for valid field names, `_min`/`_max` range rules, the
`numeric_multi` first-entry comparison caveat, and the error contract. A stale
reference produces confidently wrong queries.

Bump `version` in `.claude-plugin/plugin.json` **and** `.codex-plugin/plugin.json`
on each release so installed users on both platforms receive the update.

## Citation

If you use the SAFE database in your work, please cite:

> da Silva Garcia Leite, L., Zhang, B., Acar, Z., Elowitt, J., Augustine, L.J.,
> Clark, A.E., Karamalis, V., Perez, D., Schrier, J., Taylor, M. and Yang, P.,
> 2025. Creation of the Separation Archive for Elements (SAFE) Database.
> *Solvent Extraction and Ion Exchange*, pp.1-6.
