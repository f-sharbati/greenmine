# The supplied lockfile retains every existing dependency version.
# Only Leaflet and its type dependencies are added to the verified prior image.
FROM greenmine:auth-password-20261031 AS build
USER root
RUN rm -rf /app/.next
COPY --chown=node:node package.json package-lock.json /app/
COPY --chown=node:node node_modules/leaflet /app/node_modules/leaflet
COPY --chown=node:node node_modules/@types/leaflet /app/node_modules/@types/leaflet
COPY --chown=node:node node_modules/@types/geojson /app/node_modules/@types/geojson
COPY --chown=node:node app /app/app
COPY --chown=node:node components /app/components
COPY --chown=node:node lib /app/lib
COPY --chown=node:node public /app/public
COPY --chown=node:node scripts /app/scripts
RUN node scripts/test-export.cjs && npm run build

FROM greenmine:auth-password-20261031 AS runtime
USER root
RUN rm -rf /app/.next && rm -f /app/server/test_password_mode.py
COPY --from=build --chown=node:node /app/.next /app/.next
COPY --from=build --chown=node:node /app/app /app/app
COPY --from=build --chown=node:node /app/components /app/components
COPY --from=build --chown=node:node /app/lib /app/lib
COPY --from=build --chown=node:node /app/public /app/public
COPY --from=build --chown=node:node /app/scripts /app/scripts
COPY --from=build --chown=node:node /app/node_modules/leaflet /app/node_modules/leaflet
COPY --from=build --chown=node:node /app/node_modules/@types/leaflet /app/node_modules/@types/leaflet
COPY --from=build --chown=node:node /app/node_modules/@types/geojson /app/node_modules/@types/geojson
COPY --chown=node:node server /app/server
COPY --chown=node:node package.json package-lock.json RELEASE-MANIFEST.json RELEASE-1.4.1.md RELEASE-1.4.2.md ANDROID_BUNDLED_UI.md AUTHENTICATION.md DEPLOYMENT.md /app/
ENV GREENMINE_AUTH_MODE=email_otp
USER node
