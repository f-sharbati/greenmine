FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY mehrava_sharbati/package*.json ./
RUN npm ci --no-audit --no-fund
COPY mehrava_sharbati/ ./
RUN npm run build

FROM node:22-bookworm-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY mehrava_sharbati/server/requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
COPY --from=build --chown=node:node /app /app
COPY --chown=node:node *.py /opt/greenmine/python/codes/
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PYTHON_EXECUTABLE=/opt/venv/bin/python GREENMINE_PYTHON_ROOT=/opt/greenmine/python
COPY --chown=node:node ["python project/202608.CSV", "python project/202609.CSV", "/opt/greenmine/python/"]
RUN install -d -o node -g node -m 0700 /data
ENV GREENMINE_DATA_DIR=/data
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["npm", "start", "--", "--hostname", "0.0.0.0"]
