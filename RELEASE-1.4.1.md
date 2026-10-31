# GreenMine 1.4.1

- Removed the Tehran KACO pilot selector and preset from plant settings. Saving settings uses `calibration_profile: none`; the original prediction algorithms and historical validation code remain intact. Existing stored profiles are not silently rewritten before the user saves settings.
- Added a Leaflet/OpenStreetMap location picker: click/tap, drag marker, city lookup, and coordinate entry. Tiles need internet. Attribution is visible; Android uses normal HTTP caching. No offline tile downloads or bulk prefetching.
- Increased small supporting text and validation table text to 14px with comfortable line height.
- CSV and PDF share the same section-specific report schema. Overview includes avoided CO2 in kg; carbon impact exports all recorded days with environmental equivalents; readings exports selected-period daily readings and completeness; forecast exports only forecast days, estimated carbon, revenue using its own tariff, and source. No forecast means no forecast export. The PDF also retains retrospective validation when available.
- Added `/download`, linked from landing navigation and footer, with `/downloads/GreenMine-1.4.1.apk`.
- Android 1.4.1 (versionCode 8) bundles the current UI including the download page. API requests still go to `https://greenmineapp.ir`. Download links open the external browser.

## Deployment

Use this source as the Next.js project root. Preserve `/data`, especially `accounts.sqlite3`, `recovery.key`, and private `mail.json`, and preserve `/opt/greenmine/config/mail.env`. Do not overwrite them with development data. Follow `DEPLOYMENT.md` and `AUTHENTICATION.md` for the existing Python/OTP setup.

Run `npm ci`, `node scripts/test-export.cjs`, and `npm run build`; restart the existing application service with its production environment. Keep `public/downloads/GreenMine-1.4.1.apk` in the deployed application. Verify `/download` and the APK URL return 200, then verify the downloaded APK checksum matches the supplied checksum. The download URL only becomes publicly available after deployment.

For later Android changes: build Next.js first, build the Android app, then copy its APK into `public/downloads`. That directory is deliberately excluded from APK assets, avoiding recursively packaging the APK inside itself. The supplied APK uses the existing debug identity/signature so it updates the current phone installation; a store release requires your release signing configuration.

## Verification

- Production Next.js build and TypeScript checks.
- `node scripts/test-export.cjs`: report columns/conversions, forecast-only rows and tariff, empty forecasts, Persian dates, and CSV formula escaping.
- Physical-phone instrumentation uses test-only dashboard responses, leaving production accounts/data untouched; it checks layouts, map selection, report routing, and the bundled download page.

Map references: https://leafletjs.com/examples/quick-start/ and https://operations.osmfoundation.org/policies/tiles/.
