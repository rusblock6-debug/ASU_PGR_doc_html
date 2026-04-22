# settings-server

## Runtime notes

- `POST /api/secrets/{vehicle_id}` writes merged secrets into Vault.
- `.env_bort_template` is read from disk at request time (`POST` and `GET /api/secrets/{vehicle_id}`),
  so template updates do not require service restart.
- Optional best-effort notification to `settings-bort` is configured by env vars:
  - `BORT_NOTIFY_ENABLED`
  - `BORT_NOTIFY_URL_TEMPLATE` (example: `http://host.docker.internal:8017/api/admin/sync/{vehicle_id}`)
  - `BORT_NOTIFY_FORCE`
  - `BORT_NOTIFY_TIMEOUT_SEC`
  - `BORT_NOTIFY_MAX_ATTEMPTS`
  - `BORT_NOTIFY_RETRY_DELAY_SEC`
