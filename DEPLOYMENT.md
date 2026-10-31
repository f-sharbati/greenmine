# GreenMine deployment — 2026-10-31 / Android 1.3.1

**Android 1.4.0 supersedes the shell-only APK notes below.** The current normal APK embeds the UI/assets and uses greenmineapp.ir for API requests. Build the website first and then build Android to include matching UI assets. See `ANDROID_BUNDLED_UI.md`. Deploying the backend alone does not replace an already bundled Android interface; rebuild the APK for future UI changes.

**Authentication update:** this release now requires email activation for sign-up and an email OTP after password validation for new logins. Read `AUTHENTICATION.md` and bootstrap fresh SMTP with `server/configure_mail.py` **before restarting the updated service**. A blank SMTP password is insufficient. Existing data and sessions are retained; old scrypt password hashes migrate on successful password checks. No additional native APK change is required for this shared authentication update.

The deployment ZIP is laid out with the Next.js project at its root and the original Python project in `python/`. It contains source, lockfile, public assets/fonts, Android source, original prediction code, pilot reference measurements and model tests. Build dependencies and generated build output are excluded so they can be installed for the Linux server.

## Expected layout

```text
/opt/greenmine/
  package.json
  package-lock.json
  app/
  components/
  lib/
  public/
  server/
    reference_data/
  python/
    codes/prediction_engine.py
    202608.CSV
    202609.CSV
  .env.production.example
  DEPLOYMENT.md
/data/accounts.sqlite3
/data/mail.json
/opt/greenmine/config/mail.env
/opt/venv/bin/python
```

If your existing Next.js working directory differs, keep that layout and point `GREENMINE_PYTHON_ROOT` to the extracted `python` directory. The app must run with the Next.js project root as its working directory. The ZIP does not change an existing service or reverse proxy automatically.

## Deploy

1. Take a consistent SQLite backup of `/data/accounts.sqlite3` using SQLite's backup facility. Retain private environment/mail files and the existing `/data` volume. Extract the ZIP into a staging directory, then copy its application files to the existing app directory. The ZIP excludes live databases, mail configuration, local credentials and `.env.production`.
2. Use Node.js **20.9 or newer** (the installed Next.js package's minimum) and Python **3.11–3.13** with a virtual environment. An existing compatible Node/Python setup can be retained.
3. From the application root, install the locked Node dependencies and Python requirements:

   ```bash
   npm ci
   /opt/venv/bin/python -m pip install -r server/requirements.txt
   ```

4. Keep these variables in your existing private service environment or `.env.production`. `.env.production.example` is supplied as a template:

   ```dotenv
   NODE_ENV=production
   NEXT_TELEMETRY_DISABLED=1
   APP_ORIGIN=https://greenmineapp.ir
   GREENMINE_DATA_DIR=/data
   GREENMINE_PYTHON_ROOT=/opt/greenmine/python
   PYTHON_EXECUTABLE=/opt/venv/bin/python
   GREENMINE_ADMIN_EMAIL=fazi.sharbati@gmail.com
   SMTP_REQUIRE_SETUP=1
   ```

   Preserve `/opt/greenmine/config/mail.env` at mode 600 and keep `/data/mail.json` private. Load the mail environment using your existing process manager. SMTP configuration is not embedded in the ZIP or APK. No `NEXT_PUBLIC_` variable should contain a mail password.

5. Build in the project root:

   ```bash
   npm run build
   ```

   Tests must use a disposable data directory, not the live database. This example verifies the packaged original Python path as well:

   ```bash
   GREENMINE_PYTHON_ROOT="$PWD/python" /opt/venv/bin/python -m unittest discover -s server -p 'test_*.py' -q
   ```

   The test suites create their own temporary account databases; do not point manual smoke-test users or sample imports at production accounts.

6. Restart your existing GreenMine service with the updated files/environment. Its equivalent start command is `npm run start -- --hostname 127.0.0.1 --port 3000`. Keep the existing HTTPS reverse proxy for `greenmineapp.ir`. Do not run the development server in production.
7. Verify the landing page, sign-in, CSV/PDF export, and forecast. Use a designated test account. In Plant settings, the optional **Load confirmed 11.4 kW pilot settings** action enables the site-specific reference model. Review `PREDICTION_NOTES.md` before interpreting its accuracy metrics.

The app adds `calibration_references` and `forecast_runs` tables if missing. Existing accounts, readings and SMTP setup are retained. Reference JSON files in `server/reference_data/` must be deployed with the Python service. All Python modules and reference JSON are included in Next.js output tracing; the separate original engine in `python/` still needs its configured path.

## Android

- **GreenMine 1.3.1-connected**, package `ir.greenmine.app.debug`: connects to `https://greenmineapp.ir` and works independently of USB after website deployment. It receives UI and algorithm updates from that server. This is a debug-signed device/testing build; use your own release signing key for public distribution.
- **GreenMine Preview 1.3.1-preview**, package `ir.greenmine.app.preview`: connects to localhost and requires the computer server plus USB forwarding. It lets you review the latest local changes before deployment.

Normal hosted builds use `assembleDebug` with no local-backend property. Preview builds use `assembleDebug -PgreenmineLocal=true`. Both preserve their respective app data when installed as updates with the same signing key.

The prediction-only changes do not inherently require replacing a compatible Android shell. This version also restores the regular GreenMine icon to the hosted server after earlier USB testing.

## Verification for this package

Both APKs were installed on the connected Moto G84 and their installed version was checked: 1.3.1, versionCode 6. The Preview physical-device suite passed, including pilot preset form validation, measured-error display, live forecasting, scenario forms, PDF export, Persian text/number/date formatting, viewport containment and mobile/desktop layouts. The backend's 76 tests and Next.js production build passed for the included prediction changes.

Hosted landing and dashboard returned HTTP 200 from the computer. The hosted Android authentication-screen check timed out; it is not marked as passed. The public server has not been updated by this task. Deploy this ZIP and verify the regular app's sign-in flow after the release.
