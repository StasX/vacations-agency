# Development and production configuration

| Configuration | Development | Production |
| --- | --- | --- |
| Compose files | `docker-compose.yml` + `compose.development.yml` | `docker-compose.yml` |
| Environment template | `config/development.env.example` | `config/production.env.example` |
| Django settings | `api.settings.development` | `api.settings.production` (also the `api.settings` default) |
| Flask profile | `APP_ENV=development` | `APP_ENV=production` (default) |
| Python servers | Django runserver and Flask debug server | Gunicorn |
| React server | Vite with source reload | Built assets served by Nginx |
| Cookie Secure flag | Off for local HTTP | Always on |
| CSRF protection | Enabled | Enabled |
| Published ports | Loopback 3000, 5000, 8000 | Loopback 3000, 5000 |

The base Compose file explicitly selects production, even if development variables
are supplied accidentally. Only the development override selects development
profiles and reload commands. Production settings ignore attempts to enable debug
or disable secure cookies using the old switches. Hosts, CORS origins, CSRF trusted
origins, credentials, and token issuer/audience remain deployment-specific values.

## Local Docker development

From the repository root:

```sh
cp config/development.env.example .env.development
docker compose --env-file .env.development -f docker-compose.yml -f compose.development.yml up -d --build
```

Open Flask at `http://localhost:5000` and React at `http://localhost:3000`.
Django is available directly at `http://localhost:8000`. MySQL and Redis are
accessible only inside Docker. The development template contains public local-only
credentials; never use them in production. Application source is bind-mounted
while Python dependencies remain in the images. React dependencies live in a
development-only named volume. Rebuild after Python dependency changes. After
changing React dependencies, refresh its dependency volume with:

```sh
docker compose --env-file .env.development -f docker-compose.yml -f compose.development.yml run --rm --no-deps vacations-statistics-frontend npm ci
```

Vite proxies `/api/` to Django using the server-only `API_PROXY_TARGET` setting.
Without it, local `npm start` still proxies to `http://127.0.0.1:8000`. Browser
API URLs stay relative and do not contain infrastructure credentials.
The proxy preserves the browser's Host and Origin, matching production Nginx.
Rewriting Host to the internal Django address causes host-allowlist failures or
CSRF origin mismatches; adding broad trusted origins is not needed for same-origin
requests. Restart Vite after changing its configuration or proxy target.

The override names its project `vacations-development`, so its databases, Redis,
and uploads use separate project volumes. Do not attach production volumes to this
project. Use the same `--env-file` and `-f` arguments for `logs`, `down`, rebuilds,
and database maintenance. Do not use `down --volumes` to stop a persistent deployment.

## Production

```sh
cp config/production.env.example .env.production
# Supply unique secrets, real hostnames/origins, and the existing legacy salt.
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production up -d --build
```

Required passwords and signing secrets are empty in the production template;
Compose refuses to start until those required values are supplied. Keep real
environment files out of version control. `.env.*` files are also excluded from
application build contexts. Existing `.env` deployments remain supported through
Compose's default environment-file loading, but the base file now enforces
production settings. `example.env` is a legacy template; use the separate templates
for new deployments. Compose passes values explicitly and disables backend dotenv
discovery, so containers do not load another project's environment file.

Serve both applications through an HTTPS reverse proxy. On the Docker host, route
the catalog domain to `127.0.0.1:5000` and dashboard domain to `127.0.0.1:3000`.
Nginx inside the dashboard container forwards `/api/` to Django. Preserve the public
Host header and configure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`
for the dashboard's actual hostname and HTTPS origin. Keep localhost in allowed
hosts for the container health check. TLS termination/certificates are supplied by
the deployment's reverse proxy, not by this Compose file. The production profile
needs HTTPS for browser sessions; use the development profile for local HTTP.

Moving from an existing deployment: keep its current Compose project name and
database/image volume names, database credentials, signing secrets, issuer/audience,
and legacy password salt when copying settings into `.env.production`. Renaming
the environment file does not migrate or replace stored data. Production retains
the original explicit container names; development uses a `vacations-development-`
prefix. The default production project name and volume keys remain unchanged.
The two profiles use overlapping
host ports by default; stop the other stack or customize port mappings to run
both simultaneously. Services now publish only on host
loopback, so remote access must go through the HTTPS proxy. Run schema upgrades
with the selected environment explicitly:

```sh
docker compose --env-file .env.production build database-migrations
docker compose --env-file .env.production run --rm database-migrations --plan
# Back up and review the plan before applying:
docker compose --env-file .env.production run --rm database-migrations --apply
```

See [shared schema ownership and migrations](database-ownership.md) for recovery.

## Running backends outside Docker

Export the development template's values into the process environment, including
`DJANGO_SETTINGS_MODULE=api.settings.development` and `APP_ENV=development`, and point
MySQL/Redis settings at accessible local services. The Docker development database
services do not publish ports. From `Django/src`, run `python manage.py runserver`;
from `Flask/src`, run `flask --app app run --debug`. The servers bind to loopback
by default outside Docker. From `React`, run `npm start`.

Tests use their own isolated settings/environment. Browser tests explicitly select
development settings with Django debugging off for their disposable HTTP network;
they do not use deployment environment files or persistent application volumes.
