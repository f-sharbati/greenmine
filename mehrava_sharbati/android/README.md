# GreenMine for Android

Android Studio project for the existing bilingual Next.js app. The Android shell uses WebView and native Storage Access Framework dialogs for CSV import/export. It preserves the same React/Motion interface, Anjoman font, FA/EN preference, RTL layout, plant settings and original Python predictions. It is a connected app: Python runs on the server, not inside the APK.

## Use your connected phone

From `mehrava_sharbati`:

```powershell
./scripts/android-usb.ps1
```

The script finds a single authorized phone (or accepts `-Serial DEVICE_ID`), builds the APK if absent, starts a hidden production web server on **127.0.0.1:3001**, forwards the phone's port 3000 to it over USB, installs the debug app, and opens the dashboard. It builds the website if no production build exists. The usual development server on port 3000 is independent.

Keep the computer server running and USB connected. After unplugging/reconnecting USB, rerun the script. The debug app shows a bilingual Retry screen if the server cannot be reached. It does not work independently/offline.

After changing web code:

```powershell
./scripts/android-stop-server.ps1
npm run build
./scripts/android-usb.ps1
```

Logs and the managed server PID are in `.local/`, outside tracked source. `android-stop-server.ps1` stops only the process started for this project. The web app and original Python files must remain together as documented in the parent README.

## Android Studio

Open this `android` directory in Android Studio. Let Gradle sync. Choose the **app** run configuration and your connected phone. Select the **debug** variant. Run the USB script first to prepare the backend/port forwarding, then use Studio's Run button for Android changes.

The project uses AGP 8.12.0, Gradle 9.3.1, Java 17 source compatibility, compile/target SDK 35, min SDK 26. It builds with the installed Android Studio JBR and SDK. `local.properties` is machine-specific and ignored. The debug application ID is `ir.greenmine.app.debug` so it can coexist with a future release.

```powershell
./gradlew.bat assembleDebug
```

APK: `app/build/outputs/apk/debug/app-debug.apk`.

## Device verification

The dependency-free instrumentation runner checks loaded production data, FA/EN direction, minimum caption sizes, viewport overflow, settings, readings, carbon impact and the native document pickers. Screenshots are captured inside the app's private files for review.

```powershell
./gradlew.bat assembleDebugAndroidTest
adb install -r app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
adb shell am instrument -w ir.greenmine.app.debug.test/ir.greenmine.app.DeviceSmokeTest
```

Verified on the connected Moto G84 5G (Android 15/API 35). The production build is used for USB testing because the local development server stalled during client initialization in the WebView.

## A distributable release

Host the Node + Python application at an HTTPS origin, add production authentication/storage as described in the parent README, then build with:

```powershell
./gradlew.bat assembleRelease -PgreenmineUrl=https://your-real-host
```

No production URL has been invented or configured. Release builds require an explicit HTTPS URL and release signing via Android Studio. Cleartext is disabled for release. Debug cleartext is restricted to loopback. External HTTPS links open outside the app. No general JavaScript-to-Java interface, broad storage permission, camera permission, or SSL bypass is used.

References: [Android WebView](https://developer.android.com/develop/ui/views/layout/webapps/webview), [ADB](https://developer.android.com/tools/adb), [WebChromeClient](https://developer.android.com/reference/android/webkit/WebChromeClient).
