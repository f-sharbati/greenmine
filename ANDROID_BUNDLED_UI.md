# Android 1.4.0: bundled interface, hosted API

The earlier APKs contained only a WebView shell, so they displayed whatever UI was deployed on greenmineapp.ir. Reinstalling that shell could not deliver local layout/image changes. Version 1.4.0 embeds the current production-built Next.js documents, client chunks, CSS, fonts and public images in the APK.

- Regular GreenMine: `ir.greenmine.app.debug`, versionCode 7, `1.4.0-bundled`.
- The image, layout and interface load from APK assets. The app opens the landing page.
- `/api/*` requests still go to `https://greenmineapp.ir` using the existing first-party cookies, origin checks and TLS. No authentication bypass or local prediction API is shipped.
- The website/backend still needs the matching deployment and fresh SMTP setup for new OTP and prediction features. The auth screen identifies a server that needs updating.
- No USB/computer is required for the bundled interface. Internet/server access is required for real accounts, mail delivery, stored readings and calculations.
- Future changes to the embedded UI require rebuilding the APK. Server-side data and algorithm changes can still be deployed to the API independently, provided its contract remains compatible.

## Build

From the Next.js project root:

```text
npm ci
npm run build
```

Then run `assembleDebug` from `android/` with the existing Gradle wrapper and Android SDK/JDK. Do not set `greenmineLocal=true` for the normal server-connected APK. Gradle's `bundleWebUi` task copies generated web assets into the APK and requires a completed `.next/BUILD_ID`.

The resource packaging configuration explicitly retains underscore-prefixed directories; AAPT's default filter otherwise drops `_next` and `_pages`. Verify the APK contains `assets/web/_pages/index.html`, `assets/web/_pages/dashboard.html`, `assets/web/_next/static/`, and `assets/web/images/solar-minimal-wide.png`.

`MainActivity` intercepts only bundled GET assets/documents at the configured origin. API requests always use the real server. Missing local Next.js chunks return 404 rather than mixing in an older server build. Android navigation uses complete documents instead of fetching RSC payloads from a potentially older hosted Next.js release. Resource cache is refreshed on UI version updates; account cookies/storage are retained. Release builds continue to require the owner's release signing configuration.

## Verification

Installed over the regular GreenMine app on the connected Moto G84. Device tests verify new wide imagery, separated hero content at 320/360/390/430 CSS px, positive spacing between the mobile photo/instrument cards, dark theme, FA layout and the preserved three-column desktop instrument grid. Dashboard layout tests supply test-only fixture API responses in the instrumentation process; they do not create production accounts or bypass authentication in the app. The test restores the actual API client before leaving the landing page.
