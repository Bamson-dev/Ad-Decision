# Storage

Current production backend: **JSON file** at `{ADLEY_DATA_DIR}/users.json` (default `/data/users.json` in Docker).

## Planned backends

| `STORAGE_BACKEND` | Env vars | Notes |
|-------------------|----------|--------|
| `json` (default) | `ADLEY_DATA_DIR` | Mount a Coolify persistent volume at `/data` |
| `postgres` (future) | `DATABASE_URL` | Same Coolify stack, internal hostname e.g. `postgres` |
| `redis` (future) | `REDIS_URL` | Sessions/cache; internal hostname e.g. `redis` |

When Postgres support is added, set `STORAGE_BACKEND=postgres` and `DATABASE_URL` in Coolify — no Render/Railway-specific configuration required.
