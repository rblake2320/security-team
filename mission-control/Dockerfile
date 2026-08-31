FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ARG AEGIS_WEB_BUILD=operator
RUN if [ "$AEGIS_WEB_BUILD" = "showcase" ]; then npm run build:showcase; else npm run build; fi

FROM python:3.12-slim@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217 AS runtime
ARG AEGIS_COMMIT=unknown
LABEL org.opencontainers.image.revision="$AEGIS_COMMIT"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --system aegis && useradd --system --gid aegis --home-dir /app aegis
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY aegis_platform/ ./aegis_platform/
COPY migrations/ ./migrations/
COPY alembic.ini saas_server.py server.py ./
COPY deploy/vps/entrypoint.sh /usr/local/bin/aegis-entrypoint
COPY --from=web-build /build/web/dist ./web/dist/
RUN sed -i 's/\r$//' /usr/local/bin/aegis-entrypoint \
    && chmod 0555 /usr/local/bin/aegis-entrypoint \
    && mkdir -p /var/lib/aegis/evidence \
    && chown -R aegis:aegis /app /var/lib/aegis
USER aegis
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3).read()"]
ENTRYPOINT ["aegis-entrypoint"]
