# GreenMine homeowner application

Live URL: https://greenmineapp.ir. See DEPLOYMENT.md for deployment layout, environment and Android connection modes.

New accounts begin empty. Download optional sample CSVs from the dashboard and import them yourself. The supplied August/September files contain 61 dates totaling 3930.115 kWh. Exports from multiple inverter sources are stored separately and summed by day, with replay/conflict protection and incomplete-coverage warnings.

Main plant inputs are total capacity and city/location; individual panel or inverter inventories are not required. The aggregate solar model uses site geometry and imported history. Choose next Persian month or 30 days beginning today. Available weather coverage and climate fallback are visible. Annual output is an unadjusted climate baseline, not a validated annual forecast. Accuracy remains subject to independent evaluation.

Passwords use versioned PBKDF2-HMAC-SHA-256. Registration activates the account through an email OTP; login requires password validation and a second email code. Configure private SMTP before deploying this release. See AUTHENTICATION.md for the flow, setup and migration.

Install Python dependencies from server/requirements.txt and run npm ci. Set PYTHON_EXECUTABLE to the virtual-environment Python. Run npm run build and python -m unittest discover -s server -p 'test_*.py'. Use a disposable account/database for manual smoke tests. Public flow and physical Android-device acceptance are separate checks; no new signed APK is claimed.

## Current backend integration (2026-10-31)

See INTEGRATION.md for the merged GitHub revision, production environment, Android connection modes, and verification results. The authenticated account backend replaces the old in-memory-only dashboard. Android now defaults to https://greenmineapp.ir; USB mode is opt-in. The mobile landing fix is local until deployed.
