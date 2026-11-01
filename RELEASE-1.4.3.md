# GreenMine 1.4.3

The overview's Generate forecast button now mounts the forecast panel immediately while the previous panel fades out. The departing panel is removed from normal layout and made inert, so its nested exit animations cannot hold up the requested tab. Forecast values and card reveals update normally, including when the API responds during the transition.

Verified with production UI assets in Edge/Chromium using test-only API responses: the previous 1.4.2 UI reproduces the hidden-content failure, and the fix passes at 1280px and 390px, with 0ms, 250ms and 1600ms forecast delays, and three consecutive shortcut visits per case. Production build/TypeScript and section-specific export checks pass.

The Android build is 1.4.3-bundled, versionCode 10. The landing download page points to `/downloads/GreenMine-1.4.3.apk`. Deploy this complete source and its public APK; preserve existing private `/data` and mail configuration as described in DEPLOYMENT.md. No server deployment is performed by creating this package.

To run the browser regression locally: `npm install --prefix .local/ui-qa playwright-core --no-audit --no-fund`, then `node scripts/test-forecast-shortcut.cjs`. It uses the installed Microsoft Edge browser and intercepts all test requests without writing accounts or contacting weather services. `--baseline` additionally requires extracted 1.4.2 bundled assets under `.local/shortcut-baseline`.
