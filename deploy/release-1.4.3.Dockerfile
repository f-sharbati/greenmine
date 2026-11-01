# 1.4.3 retains the locked dependencies and backend from verified 1.4.2.
FROM greenmine:1.4.2 AS build
USER root
RUN rm -rf /app/.next
COPY --chown=node:node app/globals.css /app/app/globals.css
COPY --chown=node:node components/animated-card.tsx components/greenmine.tsx components/download-page.tsx /app/components/
COPY --chown=node:node public/downloads/GreenMine-1.4.3.apk public/downloads/GreenMine-1.4.3.apk.sha256 /app/public/downloads/
RUN node scripts/test-export.cjs && npm run build

FROM greenmine:1.4.2 AS runtime
USER root
RUN rm -rf /app/.next
COPY --from=build --chown=node:node /app/.next /app/.next
COPY --from=build --chown=node:node /app/app/globals.css /app/app/globals.css
COPY --from=build --chown=node:node /app/components/animated-card.tsx /app/components/greenmine.tsx /app/components/download-page.tsx /app/components/
COPY --from=build --chown=node:node /app/public/downloads/GreenMine-1.4.3.apk /app/public/downloads/GreenMine-1.4.3.apk.sha256 /app/public/downloads/
COPY --chown=node:node RELEASE-MANIFEST.json RELEASE-1.4.3.md /app/
COPY --chown=node:node scripts/test-forecast-shortcut.cjs /app/scripts/
USER node
