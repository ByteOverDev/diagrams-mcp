FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser

WORKDIR /app
COPY --chown=appuser:appuser . .
RUN pip install --no-cache-dir .

USER appuser

ENV FASTMCP_TRANSPORT=http
ENV FASTMCP_HOST=0.0.0.0

CMD ["sh", "-c", "FASTMCP_PORT=${PORT:-8000} diagrams-mcp"]
