# settings-bort

## Admin UI and API

- UI: `GET /admin`
- Runtime config: `GET /api/admin/config`, `POST /api/admin/config`
- Connection checks: `POST /api/admin/test-connections`
- Init secrets: `POST /api/admin/init/{vehicle_id}`
- Sync secrets (webhook/poll helper): `POST /api/admin/sync/{vehicle_id}?force=false`
- Export `.env`: `POST /api/admin/export-env`
- Read local secrets: `GET /api/admin/secrets` (same storage as `GET /api/secrets`)

Local secrets/runtime config are stored in local SQLite file `./data/settings_bort.db`.
If `BORT_ENV_OUTPUT_PATH` is set, secrets are exported to this `.env` file after init.

`/api/secrets/init/{vehicle_id}` resolves `SETTINGS_URL` in this order:
1. URL from saved runtime config (UI)
2. environment variable `SETTINGS_URL`

## Auto init via env

You can initialize without opening `/admin`:

- `SETTINGS_URL` - settings-server URL
- `ENTERPRISE_SERVER_URL` - enterprise-server URL
- `SETTINGS_BORT_DATABASE_URL` - optional DB URL for settings-bort itself (default SQLite)
- `VEHICLE_ID` - fallback vehicle id for auto init
- `AUTO_INIT_ENABLED` - enable startup auto init loop (`true`/`false`)
- `AUTO_INIT_VEHICLE_ID` - explicit vehicle id for auto init (priority over `VEHICLE_ID`)
- `AUTO_INIT_RETRY_INTERVAL_SEC` - retry interval (seconds)
- `AUTO_INIT_MAX_ATTEMPTS` - max attempts, `0` means infinite retries
- `AUTO_INIT_FORCE` - force auto init even if local settings already exist
- `AUTO_SYNC_ENABLED` - continuous background sync loop (`true`/`false`)
- `AUTO_SYNC_VEHICLE_ID` - vehicle id for background sync (priority over `AUTO_INIT_VEHICLE_ID`)
- `AUTO_SYNC_INTERVAL_SEC` - sync poll interval (seconds)
- `AUTO_SYNC_FORCE_ON_START` - force rewrite/export on first sync iteration
- `AUTO_SYNC_SETTINGS_URL` - override source URL for sync loop

When auto init is enabled and the network is temporarily unavailable, `settings-bort` keeps retrying initialization in background until success (or max attempts is reached).
When auto sync is enabled, `settings-bort` also keeps polling `settings-server` and rewrites local `.env` only if secrets checksum changed.
