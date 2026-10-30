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

Production HTTPS and the prior public signup/logout/relogin acceptance passed on 2026-10-30. The 2026-10-31 homeowner update passed 64 tests locally and inside the built image, a disposable-container signup/logout/relogin/CSV/forecast smoke test, and public owner login, CSV replay and both forecast horizons. The current verified image, runtime code revision and browser acceptance are recorded in `deploy/release.json`. Online backup restored into an isolated in-memory database with integrity_check=ok. Android device login and release signing remain unverified. No hosted CI result is claimed; tests and build ran locally and on the VPS. Public weather APIs may be unavailable; inspect forecast source/fallback metadata. Two months from one inverter cannot establish seasonal accuracy.

NASA climatology is cached by location for 30 days. If refresh fails, data up to one year old may be used with explicit stale metadata. Without usable NASA data the API reports WEATHER_UNAVAILABLE. Network connect/read timeouts are bounded; Open-Meteo failures use the disclosed climate model. `deploy/backup.py` performs an online backup and restores it into an isolated in-memory database to verify integrity.

## Existing VPS update layout

The current VPS uses greenmine-app bound to 127.0.0.1:3001, the named volume greenmine_accounts:/data, and greenmine-edge using host networking and /opt/greenmine/edge/Caddyfile. Release sources are /opt/greenmine/releases/8ff0556; build log /var/log/greenmine-build-8ff0556.log. Do not start the fresh-install Compose proxy alongside this existing Caddy instance or replace the account volume with a new project-prefixed volume. Future updates should build an explicit image tag, smoke-test with a disposable database, take a consistent backup, replace only the app container using the same volume/origin/port, and verify public health/auth before retiring the previous image. The previous authenticated image greenmine:16794d8 is retained. Follow the multi-source migration rollback restrictions below before restoring writes.


## Homeowner/judging update

New accounts start with empty production history, plant name/capacity/location. Sample files under `/samples/` are downloads only; users import them themselves. Existing account passwords and history are preserved. Main setup requests total plant nameplate capacity and city/location. Individual panel counts/models and inverter brands/capacities are not required. Optional settings retain overall performance, representative tilt/direction, tariff and precise coordinates.

Production is stored per account, source and local date in `production_readings`, with a unique composite key. Source identity uses export metadata (brand/model and serial); files without identifiers require a simple source name/selection. Replays do not add energy. Daily account totals sum sources. Coverage means all *registered* sources are present; incomplete dates are excluded from historical calibration. Do not mix externally combined totals with individual-device exports. Application-generated totals carry a Scope marker and matching reimports are no-ops. Supported daily CSV units/formats remain explicit; unknown vendor formats require an adapter/sample, not guessed units.

The aggregate-site model uses total nameplate capacity, solar position and plane-of-array irradiation via pvlib. Daily totals are distributed over estimated hourly shapes. Overall performance accounts empirically for temperature, inverter conversion and other losses; no individual inverter, thermal or bifacial-rear model is claimed. Historical correction is fit only on completed, sufficiently recent dates with complete registered-source coverage. Annual climate baseline is displayed before historical adjustment and is not an annual accuracy claim. The owner-provided Tehran benchmark is diagnostic, not a forced output.

Forecast windows are next Jalali month and 30 full calendar days beginning today in Asia/Tehran. Weather requests use `forecast_days=16`, then filter valid dates locally; mixing this parameter with explicit dates is rejected by the provider. Available weather days and climate fallback days are disclosed. Weather data is cached for one hour, NASA climatology as previously documented.

Minimum password length is 8. Email recovery uses 6-digit codes valid 10 minutes, up to 5 attempts, single-use consumption, account/IP rate limits and a keyed code hash. Password/session changes occur only after a valid code; a successful reset revokes existing sessions. `recovery.key` is generated privately in the data volume. If lost/restored differently, pending codes become invalid; users request another code. Login remains password-only; no mandatory email activation, CAPTCHA or login OTP was added.

SMTP configuration belongs in a root-only env file, `/opt/greenmine/config/mail.env`, passed to the container with `--env-file`. Variables: SMTP_HOST, SMTP_PORT, SMTP_TLS=starttls|ssl, SMTP_USER, SMTP_PASSWORD, SMTP_FROM. TLS is mandatory except for a localhost development sink. Never commit or include these values in frontend bundles. SMTP authentication was checked without sending messages; delivery acceptance is separate. `GREENMINE_SMTP_ENV_FILE` selects the optional mail env file for fresh Compose installs.

### Migration and rollback

Before promotion, take a consistent SQLite backup and stop the old app to stop writes. Starting the new service performs an additive, transaction-protected migration: legacy reading histories and import provenance are backfilled, and user/password/session rows are preserved. Validate counts, totals and replay on a backup clone first. Keep the account volume.

After this release accepts new multi-source imports, blindly running the old single-source app can desynchronize its cached history from the new canonical readings. Prefer a forward fix. A rollback must enter maintenance, preserve all post-release data, and reconcile/import it before resuming writes; do not silently restore an older backup over new user data.

### Administrator email setup

Set `GREENMINE_ADMIN_EMAIL` to the project administrator's existing email, and `SMTP_REQUIRE_SETUP=1` to require fresh credentials instead of legacy environment credentials. Only that authenticated account sees Email settings; the backend independently enforces this permission. A setup notification links the administrator to server/sender/new app password fields. Saving authenticates SMTP over TLS before atomically writing `/data/mail.json` with mode 0600. The password is never returned to the UI. Other users cannot configure global mail delivery. A failed connection leaves the prior configuration unchanged. No test email is sent. Existing sign-in passwords, sessions, settings and CSV histories are unaffected.

The legacy `test_smtp.py` contained an embedded credential and was sanitized to read environment variables. Original forecasting algorithm files remain unchanged; that diagnostic is the documented hash-check exception. Previously exposed credentials must be replaced; removing the current file does not erase Git history. Do not reuse the old credential for the new administrator setup. Until fresh setup completes, email recovery is unavailable; password login and CSV operations continue.
