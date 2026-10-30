# GreenMine production application

The `mehrava_sharbati` Next.js application is the production UI and authenticated API. The root Python files remain the original legacy application; never run its destructive `init_db.py` against production.

## Verified behavior

Email/password registration and login, HttpOnly session cookies, server-side session revocation, scrypt passwords, account-owned plant settings and CSV history, atomic import conflicts and duplicate replay, request Origin checks, and persistent SQLite storage. One plant/inverter per account. Accounts begin empty; import the provided inverter CSV files to use them. No email verification or password reset is implemented in this release. Legacy users are not migrated.

Both KACO files contain 61 daily readings totaling 3930.115 kWh. Forecasts use the existing NASA POWER/Open-Meteo model with a production-history bias correction. Calibration uses only completed recent observations, requires at least 21 days and refuses stale/extreme calibration. It is not evidence of predictive accuracy. The AC/DC capacity approximation and broader physical-model limitations remain. Annual climate estimates are not calibrated. Carbon equivalents are illustrative and are not credits or tokens; tokenization is deferred.

## Local verification

Create a Python venv and install `mehrava_sharbati/server/requirements.txt`. Run `python -m unittest discover -s mehrava_sharbati/server -p 'test_*.py'`. In `mehrava_sharbati`, run `npm ci`, `npm run build`, and start with `PYTHON_EXECUTABLE=/absolute/venv/bin/python npm start`.

`deploy/smoke.py` exercises auth, logout/relogin persistence, CSV merge and CSRF; use only a disposable database because it creates a test account. Add `--forecast` to exercise the live external providers. It never prints passwords or session tokens.

## Deployment and access

For a fresh deployment, run `deploy/bootstrap.sh` only on the intended Ubuntu VPS. Set `GREENMINE_DOMAIN=greenmineapp.ir` and run `docker compose -f deploy/compose.yaml up -d --build`. The account volume must persist across updates; never use `down -v`. Expose only SSH, HTTP and HTTPS. The web backend must remain private behind Caddy. Canonical origin is `https://greenmineapp.ir`; www redirects there. Registration requires no SMTP credentials.

Local SSH alias is `greenmine`, port 30222. No private keys, tokens, passwords, production database or signing keys are stored here. Repository authentication uses a separate repository deploy key on the operator computer, with write access scoped to this repository. Android release builds must use `-PgreenmineUrl=https://greenmineapp.ir`; a previously built APK must be checked for its embedded URL and signing identity before distribution. No physical-device acceptance is claimed.

## Backup and rollback

Back up SQLite using its online backup API or sqlite3 `.backup`, not a live copy of its database file without WAL. Store backup files outside the public web root with mode 0600, and keep a separate off-host copy. Before each upgrade, stop writes or take a consistent snapshot and verify that a copy can be opened with `PRAGMA integrity_check`. Account data is personal data.

Keep the previous container/image and release directory during promotion. Validate the new container using a disposable database, then start with the persistent account volume and switch Caddy upstream only after health/auth checks pass. For rollback switch the upstream to the last compatible authenticated image and restore a verified backup only if schema compatibility requires it. The original unauthenticated preview is not a safe public rollback target.

## Acceptance and remaining work

Production HTTPS, public browser signup/logout/relogin, settings/history persistence, both CSV imports and the calibrated forecast passed on 2026-10-30. The current verified image, runtime code revision and browser acceptance are recorded in `deploy/release.json`. Online backup restored into an isolated in-memory database with integrity_check=ok. Android device login and release signing remain unverified. No hosted CI result is claimed; tests and build ran locally and on the VPS. Public weather APIs may be unavailable; inspect forecast source/fallback metadata. Two months from one inverter cannot establish seasonal accuracy.

NASA climatology is cached by location for 30 days. If refresh fails, data up to one year old may be used with explicit stale metadata. Without usable NASA data the API reports WEATHER_UNAVAILABLE. Network connect/read timeouts are bounded; Open-Meteo failures use the disclosed climate model. `deploy/backup.py` performs an online backup and restores it into an isolated in-memory database to verify integrity.

## Existing VPS update layout

The current VPS uses greenmine-app bound to 127.0.0.1:3001, the named volume greenmine_accounts:/data, and greenmine-edge using host networking and /opt/greenmine/edge/Caddyfile. Release sources are /opt/greenmine/releases/16794d8; build log /var/log/greenmine-build-16794d8.log. Do not start the fresh-install Compose proxy alongside this existing Caddy instance or replace the account volume with a new project-prefixed volume. Future updates should build an explicit image tag, smoke-test with a disposable database, take a consistent backup, replace only the app container using the same volume/origin/port, and verify public health/auth before retiring the previous image. The previous authenticated image greenmine:823637c is retained for rollback; it includes weather caching and predates the chart visibility fix.
