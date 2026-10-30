# Vacations Agency

A containerized vacation agency platform featuring a **Flask application** for customer registration, vacation browsing, likes, and administrator vacation management, alongside a **React + Django statistics dashboard** for agency administrators. Both applications use a shared MySQL database.

![Agency Statistics Dashboard](docs/screenshots/statistics/dashboard.png)

## Features

### Customer application — Flask

- Register an account and sign in.
- Browse vacation offers with destination photos, travel dates, descriptions, and prices.
- Like or unlike vacations.
- See the number of likes on vacation cards.

### Vacation administration — Flask

- Access a separate administrator interface.
- Add new vacation offers with destination, description, dates, price, and cover image.
- Edit existing vacation details and cover images.
- Delete vacation offers.

### Agency statistics — React + Django

- Sign in to the agency-facing application.
- View registered member and total like counts.
- See vacations grouped by status: past, ongoing, and upcoming.
- Visualize likes by destination.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Customer application | Python, Flask, server-rendered frontend |
| Statistics frontend | React, TypeScript, Material UI, Vite, Nginx |
| Statistics API | Python, Django |
| Database | MySQL |
| Containers | Docker, Docker Compose |

## Architecture

```text
Customer / admin browser          Agency browser
       |                                |
       v                                v
Flask application :5000          Nginx :3000
(customers + admins)                    |
       |                         React files + /api/ proxy
       |                                |
       |                                v
       |                         Django API :8000
       |                                |
       +-------------+------------------+
                     |
                     v
                   MySQL
```

The Flask application handles customer-facing operations and vacation administration.
Nginx serves the production React build on port 3000 and forwards `/api/` requests
to `vacations-statistics:8000` on the Docker Compose network. Both backend
services work with the shared database.

React uses relative API URLs, so the browser sends requests to the same host,
port, and protocol that serve the frontend. For example, opening
`http://agency-host:3000` sends statistics requests to
`http://agency-host:3000/api/...`; Nginx forwards them internally to Django.

## Screenshots

### Customer application (Flask)

**Login**

![Customer login](docs/screenshots/agency/login.png)

**Registration**

![Customer registration](docs/screenshots/agency/register.png)

**Vacation catalog and likes**

![Vacation catalog](docs/screenshots/agency/vacations.png)

### Vacation administration (Flask)

**Administrator vacation list**

![Administrator vacation list](docs/screenshots/agency/admin/list.png)

**Add vacation**

![Add vacation form](docs/screenshots/agency/admin/add.png)

**Edit vacation**

![Edit vacation form](docs/screenshots/agency/admin/edit.png)

### Agency statistics (React + Django)

**Sign in**

![Statistics application login](docs/screenshots/statistics/login.png)

**Home**

![Statistics home](docs/screenshots/statistics/home.png)

**Statistics**

![Vacation statistics](docs/screenshots/statistics/dashboard.png)

**About**

![Statistics about page](docs/screenshots/statistics/about.png)

## Repository Structure

```text
vacations-agency/
├── Django/              # Statistics backend API
├── Flask/               # Customer and administrator application
├── MySQL/               # Database configuration
├── React/               # Agency statistics frontend
├── docs/
│   └── screenshots/     # Customer, admin, and dashboard screenshots
├── docker-compose.yml   # Service orchestration
└── LICENSE
```

## Getting Started

### Prerequisites

- Git
- Docker and Docker Compose

Clone the repository:

```bash
git clone https://github.com/StasX/vacations-agency.git
cd vacations-agency
```

Development and production use separate configuration. For local HTTP development:

```bash
cp config/development.env.example .env.development
docker compose --env-file .env.development -f docker-compose.yml -f compose.development.yml up -d --build
```

Inspect the services and logs:

```bash
docker compose --env-file .env.development -f docker-compose.yml -f compose.development.yml ps
docker compose --env-file .env.development -f docker-compose.yml -f compose.development.yml logs -f
```

Access the applications using these default ports:

| Service | Local address | Purpose |
| --- | --- | --- |
| Flask | `http://localhost:5000` | Customer catalog and vacation administration |
| React / Vite | `http://localhost:3000` | Statistics dashboard and `/api/` proxy |
| Django | `http://localhost:8000` | Development API and `/health` |

Development uses Flask/Django reload servers and Vite, with separate project
volumes. Production uses Gunicorn and Nginx, debugging off, and secure cookies.
For production, copy the production template and supply secrets and actual domains:

```bash
cp config/production.env.example .env.production
# Fill in .env.production before starting:
docker compose --env-file .env.production up -d --build
```

Production application ports bind to host loopback for an HTTPS reverse proxy;
MySQL, Redis, and Django have no published production ports. See
[configuration and deployment](docs/configuration.md) for environment selection,
TLS routing, persistent-volume compatibility, and maintenance commands.

Stop the development application with the same environment and Compose files:

```bash
docker compose --env-file .env.development -f docker-compose.yml -f compose.development.yml down
```

> **Warning:** `docker compose down -v` also removes persistent volumes, including database data.

## Image Uploads

Vacation uploads accept JPEG, PNG, and WebP files up to 5 MB and 20 million
pixels. Flask verifies and re-encodes their contents before saving them. Docker
Compose persists vacation images in the `vacation-images` named volume.

## Shared Database Ownership

The MySQL service defines all five shared tables through `MySQL/data.sql`.
Flask manages customer and vacation data; Django primarily reads statistics and
also upgrades password hashes during login. Neither backend currently runs shared
schema migrations at startup. Existing database volumes use the explicit
`database-migrations` maintenance service with `--plan` and `--apply`;
rebuilding the MySQL image does not apply seed changes to them.

See [database ownership and migrations](docs/database-ownership.md) for table
responsibilities, Django model mappings, and the deployment procedure.

## Password Storage

Account authentication status lives in Redis under `vacations:auth:status:<user_id>`;
no MySQL schema migration is required. Status keys have no expiry and use the
persistent Redis volume. From a Django shell, disable an account with
`from utils.auth_status import set_enabled; set_enabled(7, False)` and enable it
with `set_enabled(7, True)`. Each status change invalidates earlier dashboard
tokens and Flask sessions, including after re-enabling. Missing or malformed status keys deny authentication; login never creates or
repairs them. Compose runs `account-initialization` before starting either
backend. It enables every existing MySQL user whose Redis status is missing,
so seeded accounts can sign in on a fresh deployment. Existing statuses,
including disabled accounts, are never overwritten. The command can also run
manually as `docker compose run --rm account-initialization` with the selected
deployment environment. Its standalone script and container live in
`scripts/account-status/` and have no Flask or Django dependency.
New Flask registrations initialize
status atomically with `SET NX`, preserving any existing disabled status.
Dashboard login returns HTTP 403 with code `account_unavailable` when the
password is correct but the account status is missing, malformed, or disabled.
The login page asks the user to contact an administrator. Incorrect credentials
and malformed login requests continue to return HTTP 400.
If Redis data is lost, restore its backup before deploying to preserve disabled
accounts. Otherwise deployment initialization enables users with missing status;
login alone never recreates status. Redis outages block authenticated
requests. Dashboard requests also recheck MySQL for deletion, role changes, and
password changes. Previously issued tokens without the status claim require a
new login. Flask protected requests also recheck MySQL for account deletion,
role changes, and password changes. Flask sessions created before password
fingerprints were introduced require a new login. Password fingerprints are
keyed digests; password hashes are never stored in the browser session.

Flask and Django share PBKDF2-SHA256 password hashes with 1,000,000 iterations
and a random salt for each password. Existing SHA-512 hashes are upgraded on
successful login through either backend. Keep the existing `PASSWORDS_SALT`
value until all legacy accounts have migrated; new hashes do not depend on it.
Deploy both backends together so both can verify the new password format.

The SQL seed contains demo accounts with password `Abc123`, including the demo
admin. Each password uses an independently salted PBKDF2-SHA256 hash. These
public demo credentials are for local demonstrations only; remove the demo
accounts or change their passwords before production deployment.
Seed changes apply only when MySQL initializes an empty data directory; existing
database volumes require separate password resets for the old demo accounts.

## Local Frontend Development

With Node.js 24 and Django using the development settings on port 8000
(see [configuration](docs/configuration.md)):

```bash
cd React
npm ci
npm start
```

Vite serves the frontend on port 3000 and proxies `/api/` requests to
`http://127.0.0.1:8000`. The same proxy applies to `npm run preview` after
`npm run build`. In Docker, Nginx handles the proxy instead.

## Tests and CI

Both Python backends keep pytest 8.x and its plugins in `requirements-dev.txt`.
From either `Flask/` or `Django/`, using an activated Python environment:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

From `React/`, run `npm run test:ci` for the frontend tests and `npm run build`
for type checking and a production build. Backend suites include strict expected
failures for documented defects. See [Flask tests](Flask/tests/README.md),
[Django tests](Django/tests/README.md), and [React tests](React/tests/README.md)
for setup, coverage, and limitations.

Each backend's test suite uses only its own application code. The separate
[password compatibility suite](tests/passwords/README.md) checks that password
hashes work across both applications, running each backend in its own process.

The GitHub Actions workflow runs backend tests, frontend checks, and Trivy and
Bandit security scans.

## Production Hardening

- Production Compose publishes Flask and the statistics frontend only on host
  loopback for an HTTPS reverse proxy. MySQL, Redis, and Django have no published
  host ports.
- Django production settings disable debug mode and enforce secure cookies.
  Allowed hosts and CORS origins use explicit environment configuration;
  unrestricted CORS is disabled.

See [configuration and deployment](docs/configuration.md) for domain, origin,
and HTTPS reverse proxy setup.

## License

Licensed under the [Apache License 2.0](LICENSE).

## Author

[StasX](https://github.com/StasX)
