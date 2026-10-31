# Reuse the verified supplied-package image and its identical locked dependencies.
FROM greenmine:auth-20261031-6f216e03 AS build
USER root
COPY --chown=node:node server/auth_flow.py server/service.py server/test_password_mode.py /app/server/
COPY --chown=node:node app/api/auth/route.ts /app/app/api/auth/route.ts
COPY --chown=node:node components/auth-form.tsx components/auth-gate.tsx /app/components/
RUN npm run build

FROM greenmine:auth-20261031-6f216e03 AS runtime
USER root
RUN rm -rf /app/.next
COPY --from=build --chown=node:node /app/.next /app/.next
COPY --from=build --chown=node:node /app/server /app/server
COPY --from=build --chown=node:node /app/app /app/app
COPY --from=build --chown=node:node /app/components /app/components
COPY --chown=node:node deploy/password-mode-overlay.json /app/deploy/password-mode-overlay.json
COPY --chown=node:node AUTHENTICATION.md /app/AUTHENTICATION.md
COPY --chown=node:node .env.production.example /app/.env.production.example
ENV GREENMINE_AUTH_MODE=email_otp
USER node
