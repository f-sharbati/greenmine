# GreenMine

Bilingual Next.js landing page and solar analytics dashboard for the Mehrava Sharbati project.

## Run locally

From this directory:

```powershell
npm install
python -m pip install -r server/requirements.txt
npm run dev
```

Open http://localhost:3000 for the landing page or http://localhost:3000/dashboard for the workspace. Persian is the default; use EN/FA to switch. Plant settings and language persist in local storage. Uploaded readings stay in the current page session only.

## Features

- Responsive landing with project context, workflow and three documented pilot capacities.
- Dashboard: recorded energy, daily charts, next-month forecasts, carbon equivalences and readings table.
- Motion React animated tabs/reveals, accessible Radix tabs/dialogs and reduced-motion support.
- Anjoman Persian font, Persian numbers/dates and RTL layout.
- KACO semicolon exports (`Date;E[Wh]`) and `date,yield` files, with yield interpreted in Wh by the original cleaner.
- CSV export uses explicitly labelled kWh columns. It is a report, not an input file for the Wh-only importer.
- Editable capacity, performance ratio, UTM coordinates, panel angle/type, mounting and IRR tariff.

## Preserving the Python implementation

All original files in `../python project/codes` are unchanged. `server/bridge.py` imports `prediction_engine.py` directly. Forecasting, Jalali conversion, NASA POWER, Open-Meteo, revenue and impact formulas run in the original Python functions, with no JavaScript reimplementation.

The original `clean_uploaded_csv` function is loaded unchanged from `proj1.py` using Python AST. This avoids importing Streamlit and triggering its top-level database/UI side effects. The adapter normalizes KACO headers and day-first dates before calling it. The adapter also rejects negative energy readings. Duplicate dates retain the first row, as in the legacy cleaner.

The dashboard initially reads the supplied August/September 2026 inverter CSVs. Import replaces this dataset for the session. It does not write to or migrate the legacy SQLite database. Existing Streamlit authentication, email verification, certificate and minting code remains available in the original project; those workflows are not exposed by this new dashboard. This is a local single-workspace application, not a deployed multi-user service.

Default 14 kW capacity reflects the residential pilot. Initial coordinates, geometry and performance ratio are editable sample settings, not verified pilot specifications. Review them before generating a forecast.

## Hosting

The API route uses the Node.js runtime to spawn Python. Deploy on a host/container with Node and Python, retaining the sibling `python project` folder, or set `GREENMINE_PYTHON_ROOT` to its absolute location. `PYTHON_EXECUTABLE` may point to a virtual environment interpreter. See `.env.example`.

This architecture is not a static export or a Cloudflare Worker. No public deployment was made. Production hosting needs authentication/authorization and persistent per-user storage before exposing private plant data. No secrets from the legacy app are copied into the frontend.

## Verification

```powershell
npm run build
npx tsc --noEmit
python -m unittest discover -s server -p 'test_*.py' -v
```

Python tests check unchanged-source hashes, supplied-record totals, exact engine-derived impact/revenue, date handling, CSV deduplication and invalid settings. External climate services may fail independently; failures surface in the UI without fabricated forecast values. Open-Meteo may contribute zero days when the next Jalali month is outside its available forecast horizon, in which case the original engine uses NASA climatology.

See DESIGN.md for design research, source differences and generated-asset provenance. The supplied proprietary font and its license notice are preserved under public/fonts.


## Android phone app

The Android Studio project is in `android/`. A debug APK has been built and installed on the connected Moto G84 5G. Run `./scripts/android-usb.ps1` to start the production server on port 3001, reconnect USB forwarding and launch the app. This is a connected WebView app with native CSV file picking/saving; keep the PC server and USB connection active until an HTTPS backend is deployed. See `android/README.md` for Studio, release and device-test instructions.

## Updated visual direction

The interface now follows the newer cool blue/white references with a large solar scene, pale rounded instrument panels and orange chart accents. Small labels were raised approximately 2 px with a 12 px minimum. Motion animates chart bars, numerical values, performance arcs and the azimuth marker; reduced-motion preferences are respected. The dashboard gauges show configured plant parameters, not invented live sensor readings.

## Local CSV corrections, 30 October 2026

The bridge now parses Wh/kWh explicitly, retains zero and high-production days, and rejects invalid energy and conflicting duplicates. Explicit `kWh` or `Energy (kWh)` daily reports can be reimported. The legacy Python sources remain unchanged. `server/history_baseline.py` is an offline historical-mean benchmark, not yet connected to the weather forecast or UI. August-only training yields 1986.524 kWh for September against 1877.374 kWh actual (5.81% error for this single month). No general accuracy claim follows from this result.
