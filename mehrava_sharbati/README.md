# GreenMine solar application

The production application is available at https://greenmineapp.ir. See ../PRODUCTION.md for the architecture, validation and deployment limitations.

Run npm ci and npm run dev in this directory, with Python dependencies installed from server/requirements.txt. Set PYTHON_EXECUTABLE to the virtual environment executable. Sign up, configure the actual plant and import CSV history; new accounts start empty. The supplied two KACO files contain 61 daily readings totaling 3930.115 kWh.

The authenticated API saves accounts, plant settings, source CSVs and merged production history in SQLite. Forecasting uses the original Python engine plus a historical production bias correction. NASA climatology is cached with source/age metadata. Forecast output is an estimate; two months of one inverter do not validate seasonal accuracy. Original legacy Python files are unchanged and their destructive initializer is not used.

Validation: npm run build; python -m unittest discover -s server -p 'test_*.py'. There are 29 backend tests. deploy/smoke.py at repository root is for disposable test databases. Production HTTPS, signup/logout/relogin, account persistence, both CSV imports and the calibrated forecast have been exercised. Backup integrity was verified through isolated restoration.

Android is a Java WebView client in android/. Release builds require -PgreenmineUrl=https://greenmineapp.ir. The supplied handoff describes an earlier USB debug APK; its installed behavior and release signing have not been independently verified here. See android/README.md for build instructions. Tokenization remains deferred; displayed carbon equivalents are illustrative and not issued/tradable credits.
