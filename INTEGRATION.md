# Backend integration — 2026-10-31

Integrated `f-sharbati/greenmine` main at `35b1f77` (plant specification inputs), including the authenticated API, account-owned SQLite production history, multiple CSV sources, plant setup, calibration/weather modules, password recovery and admin-only mail settings. Original prediction-engine source is retained. The SMTP diagnostic was sanitized upstream; legacy credentials were not copied into the Android or frontend configuration.

Local compatibility changes: Python defaults to `python` on Windows and `python3` elsewhere; subprocess windows are hidden. Service database connections close deterministically after commit/rollback. The POSIX 0600 assertion runs on POSIX; Windows does not implement Unix permission bits. Linux mail-file permission handling is unchanged.

## Production configuration

Use `.env.production.example` for the supplied public server settings. Load SMTP environment privately from `/opt/greenmine/config/mail.env`, mode 0600. `SMTP_REQUIRE_SETUP=1` requires fresh setup by the authenticated administrator `fazi.sharbati@gmail.com`. SMTP credentials saved through that UI stay in `/data/mail.json`. Accounts and readings remain in `/data/accounts.sqlite3`. No production data, passwords, mail settings or server files were changed by this integration. No messages were sent.

The new source is local; these UI fixes have NOT been deployed to greenmineapp.ir or pushed to GitHub. Android loads the deployed website, so it receives the landing fix after the web release is deployed.

## Android

Default debug and release builds target `https://greenmineapp.ir`. The connected debug APK was installed on the Moto G84; an instrumentation check confirmed the HTTPS authentication UI loads. No production account was created or modified. Native CSV selection now supports multiple files, matching the new backend import flow. First-party session cookies are accepted and flushed when the app pauses; third-party cookies remain disabled. Release signing remains the owner's responsibility.

`./gradlew.bat assembleDebug` builds the connected app. For a local-only build use `./gradlew.bat assembleDebug -PgreenmineLocal=true`; `scripts/android-usb.ps1` explicitly selects that option and sets the phone's localhost origin for CSRF checks. Running this script replaces the connected debug app with the USB variant. Build/install the default again to restore hosted mode. You can override the HTTPS host with `-PgreenmineUrl=https://your-host`.

## Mobile landing

The narrow header now has a separate full-width dashboard button. The hero copy, proof, impact card and footer flow vertically instead of using fixed heights and overlapping absolute positioning. Both RTL and LTR styles are included. Desktop dashboard layout, chart motion and 1.5-second theme transition are retained.

## Verification

- Next.js production build passed, including `/api/auth` and `/api/engine`.
- All 64 backend tests passed locally (account isolation, recovery, SMTP permission boundaries, imports, forecast/model calculations and source integrity).
- Both local and hosted Android debug/test APK builds passed.
- Hosted Android authentication screen passed on the physical phone.
- Local runtime/landing screenshot verification was blocked by automatic approval review of both hidden and foreground test-server launches. The local instrumentation suite includes 320/360/390/430/768px landing checks, FA/EN, overlap checks, disposable local registration, settings/import persistence, logout, and desktop grid checks; these updated local UI tests are prepared but were not run in this session.

Pre-merge changed files are preserved in `../Mehrava-before-backend-merge.zip`.

## Authentication update superseding the original login flow

See AUTHENTICATION.md for the current registration/email activation and password + email OTP flow, password-hash migration and SMTP bootstrap. The earlier password-only sign-in description above records the original integration and is superseded by this update. Configure fresh private SMTP before restarting the updated service; an APK update alone cannot enable server email delivery.
