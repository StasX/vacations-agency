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

Copy `example.env` to `.env` and configure the database credentials, signing
secrets, and token settings before running the services. Review
`docker-compose.yml` before public deployment; the current configuration is
development-oriented.

```bash
docker compose up -d --build
```

Inspect the services and logs:

```bash
docker compose ps
docker compose logs -f
```

Access the applications using these default ports:

| Service | Local address | Purpose |
| --- | --- | --- |
| Flask | `http://localhost:5000` | Customer catalog and vacation administration |
| Nginx / React | `http://localhost:3000` | Statistics dashboard and `/api/` proxy |

For remote access, replace `localhost` in the browser address with the server's
hostname or IP address. The frontend does not require a separate API host setting.
Use HTTPS for remote deployments so browsers can send Django's Secure refresh
cookie. The dashboard accesses Django through Nginx at `/api/`. Django listens
on port 8000 inside the Compose network and does not publish a host port.

Flask session cookies explicitly use `HttpOnly`, `SameSite=Lax`, and `Secure`
by default. Keep `FLASK_COOKIE_SECURE=true` for HTTPS deployments. For local
HTTP development, set `FLASK_COOKIE_SECURE=false` and
`DJANGO_COOKIE_SECURE=false` in `.env` before starting the applications.

After changing the frontend or its Nginx configuration, rebuild its container:

```bash
docker compose up -d --build vacations-statistics-frontend
```

Stop the application:

```bash
docker compose down
```

> **Warning:** `docker compose down -v` also removes persistent volumes, including database data.

## Image Uploads

Vacation uploads accept JPEG, PNG, and WebP files up to 5 MB and 20 million
pixels. Flask verifies and re-encodes their contents before saving them. Docker
Compose persists vacation images in the `vacation-images` named volume.

## Password Storage

For existing MySQL volumes, apply `MySQL/migrations/001_user_active.sql` once
before deploying these backends. Fresh databases include `users.is_active`
automatically. Set it to `0` to disable an account. Disabled accounts cannot
sign in to either application or refresh dashboard sessions. Dashboard requests
recheck the current account and reject access tokens immediately after account
deletion, disabling, demotion, or a password change. Previously issued access
tokens without a password fingerprint require a new login after deployment.

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

With Node.js 24 and Django running locally on port 8000:

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

The GitHub Actions workflow runs backend tests, frontend checks, and Trivy and
Bandit security scans.

## Possible Improvements

- Restrict public exposure of internal services.
- Harden Django debug, allowed-host, and CORS settings for production.
- Document database ownership and migrations between the two backends.

## License

Licensed under the [Apache License 2.0](LICENSE).

## Author

[StasX](https://github.com/StasX)
