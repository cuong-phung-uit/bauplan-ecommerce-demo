# Bauplan e-commerce pipeline (agent debugging demo)

Multi-stage [Bauplan](https://docs.bauplanlabs.com/common-scenarios/multi-stage-pipelines) pipeline
(`purchase_events` -> `purchases_by_segment` -> `daily_segment_stats`) built on the tutorial dataset,
with a not-empty expectation. Used in a class demo of an AI agent debugging a Bauplan pipeline.

```
bauplan_ecommerce/        this repo
  pipeline/               the Bauplan project you run (models.py, expectations.py, bauplan_project.yml)
  CLAUDE.md               rules for the Claude Code agent
upstream_feed/            separate folder, simulates another team's feed (see step 5; not in this repo)
```

## Libraries and versions

| Where | What | Version |
|---|---|---|
| Your machine | Python | 3.10+ (tested 3.14) |
| Your machine | `bauplan` (CLI + Python SDK) | 0.3.4 |
| Bauplan runner (remote) | Python runtime | 3.11 (set in `@bauplan.python('3.11')`) |
| Bauplan runner (remote) | `polars` | 2.0.0 (pinned via `pip={'polars': '2.0.0'}`) |
| Bauplan runner (remote) | `pyarrow` | provided by Bauplan |

Only `bauplan` is installed locally. `polars` is installed by Bauplan in the remote runtime from the
`pip=` pin in each model, so there is no `requirements.txt` / `pyproject.toml`.

## Step by step

### 1. Install the Bauplan CLI and SDK
```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install bauplan==0.3.4
bauplan --version
```

### 2. Get a Bauplan account and API key (never commit it)
Sign up at https://app.bauplanlabs.com, create an API key, then store it in your local profile:
```zsh
bauplan config set api_key YOUR_API_KEY
bauplan info
```
The key is saved in `~/.bauplan/config.yaml`, outside this repo. `.gitignore` also blocks `.env`,
`*.key` and `config.yaml`. Do not paste the key into any file here.

Confirm `bauplan info` shows your username. Replace `cuong-phung-uit` below with yours.

### 3. Create your own data branch (never touch `main`)
```zsh
bauplan checkout -b cuong-phung-uit.ecommerce-pipeline --from-ref main
```
`--from-ref` is explicit on purpose: the CLI's active branch may point to a deleted branch.

### 4. Look at the source data (read-only, from main)
The tutorial dataset lives in the `bauplan` namespace on main.
```zsh
bauplan table get bauplan.ecommerce_sessions --ref main
bauplan table get bauplan.ecommerce_users --ref main
bauplan query "SELECT MIN(event_time) mn, MAX(event_time) mx, COUNT(*) n FROM bauplan.ecommerce_sessions" --ref main
```
Events cover 2019-10-01 to 2019-10-31. We use the first week.

### 5. Create the upstream feed project (outside this repo)
Simulates another team's table. It copies one week of `bauplan.ecommerce_sessions` into
`sessions_feed` and has a run parameter `event_case` (`lower` by default, `upper` uppercases `event_type`).
```zsh
mkdir -p ../upstream_feed
```

`../upstream_feed/bauplan_project.yml`
```yaml
project:
  id: 7d1f3c52-2b6e-4f0a-9a1e-5c3b8e2d4a11
  name: upstream_feed

parameters:
  event_case:
    type: str
    default: lower
```

`../upstream_feed/models.py`
```python
from typing import Annotated

import pyarrow

import bauplan


class SessionEvents(bauplan.TableSchema):
    event_time: bauplan.Any
    event_type: bauplan.Any
    product_id: bauplan.Any
    category_id: bauplan.Any
    category_code: bauplan.Any
    brand: bauplan.Any
    price: bauplan.Any
    user_id: bauplan.Any
    user_session: bauplan.Any


@bauplan.model(materialization_strategy='REPLACE')
@bauplan.python('3.11', pip={'polars': '2.0.0'})
def sessions_feed(
    raw: Annotated[
        pyarrow.Table,
        bauplan.Model(
            'bauplan.ecommerce_sessions',
            projection_schema=SessionEvents,
            filter="event_time >= '2019-10-01' AND event_time < '2019-10-08'",
        ),
    ],
    event_case: Annotated[str, bauplan.Parameter('event_case')],
) -> Annotated[pyarrow.Table, SessionEvents]:
    import polars as pl

    df = pl.DataFrame(raw)
    if event_case == 'upper':
        df = df.with_columns(pl.col('event_type').str.to_uppercase())
    return df.to_arrow()
```

Why `bauplan.Any`: the source columns are nullable, and typed fields such as `bauplan.String` fail with
`cannot cast from optional to required`.

Dry-run, run, and check:
```zsh
bauplan run --project-dir ../upstream_feed --dry-run
bauplan run --project-dir ../upstream_feed
bauplan query "SELECT event_type, COUNT(*) n FROM sessions_feed GROUP BY event_type"
```

### 6. The pipeline (`pipeline/`)
This repo's `pipeline/` folder is the tutorial's Polars variant with these changes:
- `purchase_events` reads `sessions_feed` instead of `bauplan.ecommerce_sessions`.
- `materialization_strategy='REPLACE'` on all three models.
- Source projections use `bauplan.Any` (nullable columns, as above) and `ecommerce_users` is written
  `bauplan.ecommerce_users` (namespace).
- `pl.len()` is cast to Int64, otherwise `ModelOutputContractError` (UInt32 vs Int64).

Files: `pipeline/bauplan_project.yml`, `pipeline/models.py`, `pipeline/expectations.py`.

### 7. The expectation
`pipeline/expectations.py` has `test_daily_segment_stats_not_empty`, which asserts `daily_segment_stats`
has at least one row. Strict mode stays on (the default).

### 8. Run and verify
```zsh
bauplan run --project-dir pipeline --dry-run
bauplan run --project-dir pipeline
bauplan query "SELECT * FROM purchase_events LIMIT 5"
bauplan query "SELECT * FROM purchases_by_segment LIMIT 5"
bauplan query "SELECT * FROM daily_segment_stats LIMIT 5"
```
Expected: 21 rows in `daily_segment_stats` (3 segments x 7 days).

### 9. Install the Bauplan skills for Claude Code
The demo uses the official [bauplan-skills](https://github.com/BauplanLabs/bauplan-skills) plugin
(`bauplan@bauplan-skills`, v2.6.0): `bauplan-data-pipeline` to build and `bauplan-debug-and-fix-pipeline`
to debug.
```zsh
claude plugin marketplace add BauplanLabs/bauplan-skills
claude plugin install bauplan@bauplan-skills
claude plugin list
```
Then restart Claude Code or run `/reload-plugins`. The plugin also provides `bauplan-data-quality-checks`,
`bauplan-explore-data`, `bauplan-data-semantics`, `bauplan-data-assessment`, `bauplan-dag-optimization`,
`bauplan-safe-ingestion` and `bauplan-migrate-to-typed-sdk`.

## Rules for the agent
See `CLAUDE.md`. Short version: never write to Bauplan `main`, always pass `--from-ref`, check
`bauplan <command> --help` before using flags, commit every code change.

## Security
No API key, token or secret is in this repo or its git history. Keep your key only in
`~/.bauplan/config.yaml` or the `BAUPLAN_API_KEY` environment variable.
