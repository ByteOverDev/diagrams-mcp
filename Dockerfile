FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

ENV FASTMCP_TRANSPORT=http
ENV FASTMCP_HOST=0.0.0.0

CMD ["sh", "-c", "FASTMCP_PORT=${PORT:-8000} diagrams-mcp"]
