# UI and Android update

- Mobile landing copy, calls to action, proof and impact card flow without overlap. Verified 320, 360, 390, 430 and 768 CSS-pixel widths on a physical Moto G84 WebView.
- Header profile and hamburger buttons open a shared navigation/account panel. Email wraps inside its container; admin email settings and sign-out are inside the panel. The original email-settings backend authorization remains unchanged. Escape, backdrop click, navigation and Android back close the menu. Long email addresses no longer appear as a separate overflowing account bar.
- Selected forecast-window buttons have explicit dark text on a pale background in dark mode.
- Theme transitions again reveal the complete new page through a circular View Transition mask. No opaque covering veil. Unsupported browsers and reduced-motion users switch immediately. Active CSS/WAAPI animations are paused during the theme capture/reveal and resumed afterward. Rotation, hidden tabs and unmount cancel safely.
- Reduced animation work: no backdrop blur on moving instrument cards; Intl formatters reused instead of constructed each frame; chart bars animate scaleY with fixed layout heights and one viewport observer. Motion remains timestamp-driven.
- Export chooser offers CSV or PDF using the same selected rows/forecast. PDF uses a paginated print document, Persian font and RTL, repeated table headings, and forecast disclaimer. Choose Save as PDF in the system print dialog. Browser uses an isolated print iframe; Android 1.2.0 adds an origin-checked native PrintManager bridge and WebView report renderer. English and Persian previews were visually reviewed on the phone. Existing CSV download/Storage Access Framework path remains.

## Verification

Next.js production build and Android builds passed. Device instrumentation passed FA/EN landing widths and non-overlap, visible hamburger menu, profile/email containment, session/history persistence across reload, logout, CSV/PDF chooser, Android PDF print preview and desktop/mobile dashboard layouts. Theme timing sample: 105 requestAnimationFrame intervals, p95 16.8 ms in the development WebView. This is a short timing sample, not an all-device benchmark or a before/after comparison. Native print preview was checked; no personal data or production records were used.

The existing development server initially blocked Android loopback resources. Only 127.0.0.1 was added to allowedDevOrigins; USB app uses localhost consistently to match the development CSRF origin. No production origin restrictions were relaxed. A separate production-preview server launch was rejected by automatic approval review; verification used the already-running development server after fixing its loopback configuration.

## Deployment

This is local source, not a deployment. Deploy the updated Next.js code to greenmineapp.ir and install the new PDF-capable APK for both halves of the Android experience. The default APK targets the hosted HTTPS backend. A local preview build uses -PgreenmineLocal=true and adb reverse tcp:3000 tcp:3000 when the development server is on port 3000. Existing private SMTP settings and /data/accounts.sqlite3 must be preserved. No Python algorithms or backend business logic changed in this UI update.

## 1.2.1 correction

Fixed corrupted literal question-mark Persian strings using UTF-8-safe writes: sign-out, account/profile accessibility labels, close-menu label and native PDF error. Export buttons explicitly say CSV / PDF. Desktop solar imagery covers the full overview background. Mobile overview metrics have a 14px gap instead of a negative overlap; solar scene has sufficient height for its labels. Phone instrumentation passed explicit assertions for the Persian sign-out string, CTA containment at 320/360/390/430/768px, visible PDF wording, native PDF preview, mobile gap and desktop cover background.

Android connection modes now have distinct identities: GreenMine Preview (ir.greenmine.app.preview) loads localhost over USB; GreenMine (ir.greenmine.app.debug) loads the public website. Preview 1.2.1 is installed and verified on the physical phone without replacing the hosted app or its account. The hosted website must still be deployed for the regular GreenMine icon to show the shared UI fixes. A native APK update alone cannot replace hosted page content. Run scripts/android-usb.ps1 for preview mode (its default production server uses port 3001 and reverses phone port 3000); if using the existing development server on port 3000, use adb reverse tcp:3000 tcp:3000.

## 2026-10-31 contrast, artwork and forecast follow-up

Replaced the dashboard artwork with a newly generated 1024x1536 saturated solar photograph. It fills only the dedicated photo panel; instrument cards sit on a solid theme-aware background. Mobile retains a separate photo panel and positive spacing.

Mail notification uses explicit high-contrast colors and a body portal, independent of the collapsible account menu. Required coordinates are visible in the location section; invalid optional fields expand their disclosure. Forecast requests that need configuration resume after save, preserving the requested horizon. Saving settings from the forecast tab also regenerates the result. Errors appear beside the forecast controls. Production-history adjustment remains an explicit checkbox; turn it off for a new installation without readings. No prediction algorithms changed.

Validation: production build, 64 Python tests, live NASA-backed model calculation and physical Android WebView forecast generation. The source is local; the regular hosted app requires deployment of this website update. GreenMine Preview uses the existing localhost server over USB.

## 1.3.0 localization and visual refinement

Persian UI and PDF reports share lib/format.ts: Persian digits, requested U+060C comma for thousands, decimal point, ungrouped years, and Persian-calendar date labels including rolling forecasts and climate timestamps. CSV remains machine-readable. Reporting filters retain their original Gregorian source-month boundaries but show the corresponding Persian date range.

A newly generated minimal wide solar image spans the whole desktop overview; mobile keeps a cover image and separated cards. Light-mode gauge rings, ticks, units and descriptions have stronger contrast. Forecast and carbon cards use teal, coral, lavender and green accents. Pointer hover and keyboard focus styling covers buttons, links, navigation, cards, table rows and chart items; reduced-motion users avoid hover translations.

Android 1.3.0 USB build was installed over ir.greenmine.app.debug, the regular GreenMine icon, using -PgreenmineLocal=true -PgreenminePreviewIdentity=false. This is intentionally a localhost/USB build; keep adb reverse tcp:3000 tcp:3000 and the development server running. Existing hosted cookies/data are not deleted; this build uses the separate local origin. To return to hosted HTTPS after website deployment, build without these Gradle properties. Public website has not been deployed.

## Prediction follow-up

Added opt-in confirmed 11.4 kWp / 15 kW KACO pilot calibration, frozen measured-configuration history fitting, calendar-correct Gregorian and Persian retrospective tests, monthly and daily error metrics, and saved issued forecasts with pending/complete/scenario states. The forecast PDF includes the latest retrospective error summary. Full methodology, contradictory slide totals and model comparisons are documented in PREDICTION_NOTES.md. The original Python engine is retained unchanged.

Validation: 76 Python tests, production Next.js build and live localhost API integration including doubled-capacity scenarios. Phone unavailable over ADB at final verification; browser extension host unavailable. New on-device rendering was not verified in this task. Existing USB Android shell consumes the updated local Next.js app when reconnected. No production deployment performed.

## Android 1.3.1 and deployment package

Both regular GreenMine (1.3.1-connected, HTTPS greenmineapp.ir) and GreenMine Preview (1.3.1-preview, localhost over USB) were installed on the phone. Preview passed the full physical-device suite including the new pilot preset and measured-error display. Hosted authentication verification timed out; computer HTTP checks returned 200 for landing/dashboard. No production deployment was performed. DEPLOYMENT.md documents the deployment ZIP layout, installation commands and environment. The release ZIP places Next.js at the archive root and the original Python project under python/, matching /opt/greenmine/python.

## Email activation and login OTP

Implemented the supplied flowchart: registration validates a server CAPTCHA and password confirmation, saves an inactive account and activates it only after email OTP; activation returns to sign-in. Login checks the password and requires a separate email OTP before issuing a session. New passwords use versioned PBKDF2-HMAC-SHA-256 (600,000 rounds) and legacy scrypt hashes upgrade after successful password verification. OTPs are HMAC hashed, expiring, purpose/browser bound, single-use and attempt limited. Existing accounts/data and active sessions are retained.

SMTP uses the existing private /data/mail.json and authenticated TLS transport for activation, login and recovery. SMTP_REQUIRE_SETUP=1 remains enabled; blank SMTP_PASSWORD cannot deliver codes. Run server/configure_mail.py as the application OS user before restarting this release; see AUTHENTICATION.md. The command verifies SMTP credentials and writes private configuration without sending a test email. No actual Gmail password or live email delivery was available during implementation.

The Android shell uses the shared web authentication, so no native APK replacement is required for this update. The Android auth UI instrumentation builds successfully, but the physical phone was disconnected during this task. Existing password-only dashboard instrumentation requires a provisioned test flow; default instrumentation now checks auth UI without creating accounts or sending email.

## Android 1.4.0 bundled UI correction

The previous APK was a hosted-page shell and therefore showed the older deployed UI. Version 1.4.0-bundled embeds the current Next.js HTML, scripts, CSS, fonts and images. Both landing and dashboard reference solar-minimal-wide.png directly. The app opens the landing page; mobile photo/metric spacing is positive and the decorative hotspot is clear of the heading. Server API calls remain HTTPS at greenmineapp.ir, with existing session cookies and authentication enforcement. Auth UI identifies an older backend requiring deployment.

Gradle copies the production build into APK assets and retains underscore-prefixed Next.js directories. Native navigation loads bundled documents, preventing mixing old server RSC with new assets. Production build, APK packaging and physical-device layout checks passed; dashboard visuals were tested with instrumentation-only fixture responses, not production account changes. See ANDROID_BUNDLED_UI.md. Future embedded-UI changes require an APK rebuild; API/data updates remain server-side.
