# Flask tests

From the repository root, using the Flask virtual environment on Windows:

```powershell
Flask\env\Scripts\python.exe -m pip install -r Flask/requirements-dev.txt
Flask\env\Scripts\python.exe -m pytest Flask/tests -q --cov=Flask/src --cov-branch --cov-report=term-missing
```

With another activated Python environment, use `python` in place of the executable
above. From the Flask directory, run `python -m pytest`.

The suite covers all Python application layers and both JavaScript files:

| Area | Coverage |
| --- | --- |
| Routes and templates | Public pages, login aliases, registration, logout, lists for both roles, empty lists, add/edit forms, uploads, updates, deletion, images and fallback, redirects, exception pages |
| Authorization | Anonymous access, regular-user restrictions for GET and POST, admin access, session contents |
| Models | Missing fields, length boundaries, email/password rules, dates and ordering, price limits, insert/update differences, error payloads |
| Facades and logic | Parameter binding, returned records, duplicate registration, likes toggling, model preservation on validation failure, context-manager cleanup |
| DAL | Connection options, every query operation, return values, reconnect, query/fetch failures, cursor cleanup, connection failures and close |
| Utilities and configuration | Date conversion, password salt/UTF-8, logger append behavior, environment settings, Gunicorn defaults and overrides |
| Images | Unique names, basename handling, empty uploads, replacement, missing files, save failures, fallback |
| JavaScript | Form validation, country selection, date checks, modal actions, delete confirmation, file preview, price formatting, page initialization, password visibility |

Database access is mocked and attempts to connect to MySQL fail immediately.
The DAL tests replace the connector with fake connections and cursors. Uploads
and log files use pytest's temporary directories. Session secrets and password
salt are test-only values; no running services or database credentials are required.

Node.js (22 or newer recommended) runs the dependency-free JavaScript suite via
pytest. Without Node, pytest explicitly skips that test. It can also run directly:

```powershell
node --test Flask/tests/js/ui.test.cjs
```

Known defects are executable regression tests marked as strict expected failures:

- Invalid edit submissions use incorrect country column names during recovery.
- Malformed dates and prices raise `ValueError` instead of validation errors.
- Anonymous likes produce a generic error rather than redirecting to login.
- Missing vacation records do not return 404.
- Editing without an image field fails instead of preserving the image.
- Non-image uploads are accepted by the server.
- Request-created database connections are not closed.

The JavaScript image-preview case is a Node `todo` test: selecting `imgBtnTxt`
without `#` raises a `TypeError`. The test executes and displays the failure.

When fixing these defects, remove the corresponding `xfail` markers. Strict mode
makes an unexpected pass fail the suite so a fix cannot silently leave a stale
marker. Remove the JavaScript `todo` option when fixing its defect.

Coverage measures Python statements and branches; it includes code executed by
expected-failure tests. The remaining uncovered Python code includes unreachable
empty-description checks and the broken country recovery block. Coverage does
not prove correctness of SQL against a real database.

These are isolated unit and Flask test-client integration tests. Real MySQL,
Docker startup, browser rendering, and external CDN availability are not tested.
