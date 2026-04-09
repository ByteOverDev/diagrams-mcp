FROM python:3.11-slim

# System deps: Graphviz (mingrammer/diagrams), Chromium (Mermaid), JRE (PlantUML), fonts, curl
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        graphviz fonts-dejavu-core \
        chromium \
        default-jre-headless \
        curl \
        nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Mermaid CLI (skip bundled Chromium — use system Chromium above)
ENV PUPPETEER_SKIP_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
RUN npm install -g @mermaid-js/mermaid-cli \
    && npm cache clean --force

# Puppeteer config for container compatibility
COPY puppeteer-config.json /etc/mermaid/puppeteer-config.json

# PlantUML JAR (pinned version + integrity check)
ARG PLANTUML_VERSION=1.2024.8
ARG PLANTUML_SHA256=b88519d2f37c089a470ee7044ec011a72d130e70a61f7fcaa424179f1c1f4641
RUN curl -fsSL "https://github.com/plantuml/plantuml/releases/download/v${PLANTUML_VERSION}/plantuml-${PLANTUML_VERSION}.jar" \
    -o /opt/plantuml.jar \
    && echo "${PLANTUML_SHA256}  /opt/plantuml.jar" | sha256sum -c -

RUN useradd --create-home appuser

WORKDIR /app
COPY --chown=appuser:appuser . .
RUN pip install --no-cache-dir .

USER appuser

ENV FASTMCP_TRANSPORT=http
ENV FASTMCP_HOST=0.0.0.0

CMD ["sh", "-c", "FASTMCP_PORT=${PORT:-8000} diagrams-mcp"]
