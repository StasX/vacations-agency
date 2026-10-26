# React tests

Run from the `React` directory after installing dependencies with `npm install`:

```sh
npm test                # run Jest
npm test -- --watchAll  # interactive watch mode
npm run test:unit       # isolated utility and state tests
npm run test:integration # service/store and component integration tests
npm run test:ci         # run once, suitable for CI
npm run test:coverage   # run once and generate coverage/
```

On PowerShell systems that block `npm.ps1`, use `npm.cmd` instead of `npm`.
The suite uses Jest 29, Babel, and React Testing Library 16.
TypeScript and JSX use Babel; CSS and assets use local mocks.
No running Django API, database, Docker containers, or external network is needed.

## Directory layout

```text
tests/
  unit/
    state.test.ts              # state transitions and isolation
    useTitle.test.ts           # document title hook
    Notify.test.ts             # notification wrapper
  integration/
    App.test.tsx                # components, forms, routes, and Redux
    UserService.test.ts        # authentication, storage, and Redux
    StatisticsService.test.ts  # API orchestration, refresh, and Redux
  setupTests.ts               # shared jest-dom setup
```

Unit tests exercise individual utilities or state transitions. Integration tests
exercise interactions between application components or between services,
storage, and the real Redux store. External HTTP and charts remain mocked.

## Coverage

- Authentication: credentials, rejected login, empty responses, token storage,
  session restoration, logout, refresh success, unauthorized and network failures.
- Statistics API: all four endpoints, authorization headers, cookie options,
  Redux updates, missing tokens, request errors, expired tokens, refresh retries,
  unauthorized redirects, and concurrent failures.
- Redux: initial state, every state update, immutability, slice isolation, logout.
- UI: login validation and errors, protected routes for anonymous and non-admin
  users, admin routes, default and missing routes, navigation, account name,
  logout success and failure, layout composition, footer, statistics and charts.
- Utilities: document title updates and error notifications.

HTTP calls and chart rendering are mocked; routing, Redux, form validation,
and Material UI components run normally in jsdom. Deferred promises exercise
refresh/retry coordination; controlled timers cover delayed UI rendering. These are unit and
component integration tests, not browser or live-backend end-to-end tests.
Coverage excludes the entry point, generated declarations, test setup, and
the unused CRA web-vitals helper. View `coverage/lcov-report/index.html` for details.

Tests use TypeScript (`.ts`, or `.tsx` for JSX) and typed Jest mocks.
Timer-driven React updates use `act` from `react`.
Jest transpiles TypeScript; it does not run the TypeScript compiler.

## Regression tests

All 85 tests pass; none are skipped. Regression coverage includes empty session
state, logout cookies, malformed saved tokens, refresh completion before retries,
bounded retries, concurrent refresh failures, stale responses, statistics rendering,
and header timer cleanup.

Redux serializability warnings may appear for existing model instances.
The shared tsconfig.json includes src and tests. Run npx tsc --noEmit to
check both. Jest uses Babel to transpile TypeScript.
