# integrator: a small iPaaS (Celigo-style) engine

Stdlib-only Python. A **flow** reads from a **source** connector, maps fields, and writes to a
**destination** connector, with retries, per-record error capture and delta (watermark) syncing.

## Run
```
python -m integrator validate examples/netsuite_customers_to_s3.json
python -m integrator run examples/netsuite_customers_to_s3.json [--dry-run]
python -m integrator serve FLOW --every 300 [--max-runs N]   # simple built-in scheduler
python -m integrator runs | errors [--flow NAME]
python -m integrator connectors
```
History and watermarks live in SQLite (`--db`, default `./integrator.db`, git-ignored).

## Flow file (JSON)
`name`, `source`, `destination` (each `{type, ...}`), optional `mapping`, `batch_size` (100), `retries` (3).
Secrets are never written in flow files: use `"$env:NAME"` and export the variable.

### Mapping
`mapping.fields` maps `target -> "source.path"` or `{from|const, transform, default, required}`.
Dotted paths work on both sides (`entity.id`). Transforms: `upper lower strip str int float` (list to chain).
Omit `fields` for pass-through. A record that fails mapping is logged and skipped; the run is `partial`.

## Connectors
| type | role | notes |
|---|---|---|
| `netsuite` | source, destination | Token-based auth (OAuth1 HMAC-SHA256). Source runs **SuiteQL** via REST (`query`, paged 1000). Destination uses the Record API: PUT `eid:` upsert when `external_id_field` is set, else POST. Needs `account, consumer_key, consumer_secret, token_id, token_secret`, `record_type` (dest). |
| `aws_s3` | source, destination | SigV4. Source reads every JSON / JSONL object under `prefix`. Destination writes one JSONL object per batch to `key` (`{flow} {run_id} {batch}` placeholders). Optional `endpoint` for LocalStack/MinIO. |
| `aws_sqs` | destination | `SendMessage` per record (FIFO queues get group/dedup ids). |

AWS credentials come from `access_key_id`/`secret_access_key`/`session_token` (use `$env:`) or the standard
`AWS_*` environment variables. Region is required.

## Delta sync
Set `source.delta_field` and use `{since}` in the SuiteQL. After a fully clean run the highest
`delta_field` value is saved and substituted next time (validated as a date to prevent query injection).
A run with any failed record does not advance the watermark, so failures are re-read; use idempotent
destinations (`external_id_field`, deterministic S3 keys) so reprocessing is safe.

S3 sources remember processed object keys (`seen_keys`, last 10,000) and skip them on later runs; like the
watermark, they are saved only after a clean run.

## Reliability
HTTP 429/5xx and network errors retry with exponential backoff (1,2,4.. capped at 30s) up to `retries`.
Other errors are recorded per record (`errors` command) without stopping the batch.

## Layout
`integrator/{auth,http,config,mapping,store,runner,cli}.py`, `integrator/connectors/{netsuite,aws}.py`.
Add a connector by subclassing `Connector` and registering it in `connectors/__init__.py`.

## Not built yet / caveats
- **Not verified against a live NetSuite or AWS account.** Tests use a fake transport, AWS's published SigV4
  vector, and an end-to-end run over real HTTP against a local fake S3 server. Expect to tune the SuiteQL
  date format for your account (`TO_DATE` vs `TO_TIMESTAMP`, and the format NetSuite returns for
  `lastmodifieddate`). First step with real credentials: `run --dry-run` against a sandbox.
- `serve` is a single-process interval loop; for production use cron/EventBridge calling `run`.
- Not built: web UI, webhook/SQS sources, multi-step flows or lookups.
