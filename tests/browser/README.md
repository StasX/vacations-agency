# Browser-to-backend tests

These headless Chromium tests exercise the Flask customer flow and React/Nginx/Django
administrator statistics flow against real MySQL and Redis. Requests are not mocked.
CSRF remains enabled; forms and the React client obtain tokens normally.
Secure cookies are disabled only for this isolated HTTP test environment.

Run from the repository root with Docker running:

```sh
docker compose -p vacations-browser-tests -f compose.browser-tests.yml build
docker compose -p vacations-browser-tests -f compose.browser-tests.yml run --rm browser-tests
docker compose -p vacations-browser-tests -f compose.browser-tests.yml down --volumes --remove-orphans
```

The environment has no published ports or production volumes. MySQL and Redis data
are disposable. Each test resets SQL data and Redis account statuses using the
application's restricted Redis ACL; run serially, never against a shared
environment. Failed tests retain browser traces and screenshots under
`tests/browser/reports/`, alongside JUnit results.

The customer test registers, likes/unlikes a vacation, reloads, logs in again, and
logs out, checking persisted likes in MySQL. The dashboard test signs in through
the UI, checks all four real statistics API responses and displayed seeded totals,
reloads, and logs out, checking cookie and local-storage cleanup and route access.

The Flask administrator test adds a vacation with an uploaded PNG, then edits its
country, description, dates, and price through the UI. It checks persisted MySQL
values, verifies the uploaded image loads, and reloads to confirm the update and
preservation of the existing cover image.
