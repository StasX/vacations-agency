# Vacations agency frontend

React 19 and TypeScript, built with Vite. Use Node.js 24 LTS and npm.

Run npm ci, then npm start to serve the app on port 3000.
API URLs are configured in src/Utils/AppConfig.ts.

- npm run build: type check and build into build/
- npm run preview: preview the production build
- npm run test:ci: run Jest unit and integration tests
- npm run test:coverage: generate coverage

Docker uses Node.js 24 to build and nginx to serve build/ on port 3000.
On PowerShell systems that block npm.ps1, use npm.cmd.

The Jest suite includes existing application regression tests.
See tests/README.md for coverage and known failures.
