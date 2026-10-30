# GreenMine homeowner application

Live URL: https://greenmineapp.ir. See ../PRODUCTION.md and ../deploy/release.json for operations and runtime identity.

New accounts begin empty. Download optional sample CSVs from the dashboard and import them yourself. The supplied August/September files contain 61 dates totaling 3930.115 kWh. Exports from multiple inverter sources are stored separately and summed by day, with replay/conflict protection and incomplete-coverage warnings.

Main plant inputs are total capacity and city/location; individual panel or inverter inventories are not required. The aggregate solar model uses site geometry and imported history. Choose next Persian month or 30 days beginning today. Available weather coverage and climate fallback are visible. Annual output is an unadjusted climate baseline, not a validated annual forecast. Accuracy remains subject to independent evaluation.

Passwords require 8–128 characters. Login is password-only. Optional configured SMTP enables expiring, one-time email recovery codes. No SMTP secrets or private databases belong in this repository.

Install Python dependencies from server/requirements.txt and run npm ci. Set PYTHON_EXECUTABLE to the virtual-environment Python. Run npm run build and python -m unittest discover -s server -p 'test_*.py'. Use deploy/smoke.py only with a disposable database. Public flow and physical Android-device acceptance are separate checks; no new signed APK is claimed.
