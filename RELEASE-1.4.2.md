# GreenMine 1.4.2

The location pin follows the map center while panning. Coordinates commit when movement stops, avoiding per-frame React updates. Desktop scroll-wheel zoom is enabled. Manual coordinate and city-search changes still reposition the map; map-originated updates do not reset its zoom.

Android versionCode 9 / 1.4.2-bundled includes the same change. The landing download page now links to /downloads/GreenMine-1.4.2.apk. Deploy the complete source and public APK to update the website. Preserve all existing private /data files and mail configuration. Deployment steps from RELEASE-1.4.1.md still apply, with 1.4.2 as the APK version.
