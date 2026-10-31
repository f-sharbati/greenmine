# Backend handoff (updated)

See `PRODUCTION.md` at repository root for deployment, verification and remaining limitations. The root legacy Python files are unchanged. The production app is `mehrava_sharbati`.

`app/api/auth/route.ts` implements register/login/logout/session inspection. `app/api/engine/route.ts` authenticates requests through `server/service.py`. Use matching request Origin and the HttpOnly session cookie. Engine actions are overview, import, settings and forecast. Settings accepts validated plant/tariff. Forecast takes settings/history from the authenticated account, not client-supplied ownership or readings. Accounts start empty; imports merge atomically and reject conflicts. Wh and exported kWh CSV formats are supported.

The service uses persistent SQLite in GREENMINE_DATA_DIR, default .local for development and /data in Docker. Set PYTHON_EXECUTABLE to the Python venv executable. Production APP_ORIGIN must be the canonical HTTPS origin. Never put credentials in frontend environment variables.

`server/bridge.py` adapts the original engine. `server/calibration.py` applies explicitly described production bias correction; it does not establish predictive accuracy. The original destructive initializer and email auth workflows are not invoked by this application.

Run npm ci and npm run build in the app directory; run python -m unittest discover -s server -p 'test_*.py' using the Python venv. There are 29 tests. The deploy/smoke.py integration check requires a disposable database. See android/README.md for URL/build configuration; no physical-device verification is claimed.

Current integration: see INTEGRATION.md. The source now includes authenticated APIs and persistent account-owned data; earlier descriptions of a session-only frontend no longer apply. Production configuration is documented in .env.production.example. The hosted Android app points to greenmineapp.ir.
