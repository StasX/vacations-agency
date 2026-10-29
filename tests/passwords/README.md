# Password compatibility contract

This separate suite checks that each backend can verify passwords hashed by the
other backend. Each application runs in its own subprocess; neither backend's
unit tests import code from the other application.

From the repository root, with pytest and python-dotenv installed:

```sh
python -m pytest -c tests/passwords/pytest.ini tests/passwords -q
```

No database, Redis, or running applications are required. CI runs this suite
using the Flask test environment.
