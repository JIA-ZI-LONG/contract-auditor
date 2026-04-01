FROM python:3.10-slim-bookworm AS base

# set source
# RUN pip3 config set global.index-url https://pypi.mirrors.ustc.edu.cn/simple
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/

RUN pip3 install  --progress-bar=off --upgrade setuptools==78.1.1

# install packages
FROM base as packages

# Install system dependencies only if needed (keep image small)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y --only-upgrade \
    libc6  \
    libc-bin  \
    libc-dev-bin  \
    libexpat1  \
    libgnutls30  \
    libsqlite3-0 \
    libssl3 \
    perl-base &&  \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies from requirements.txt
RUN pip install --progress-bar=off --no-cache-dir -r /app/requirements.txt

# Copy application source
COPY src /app/src

# Ensure app code is importable
ENV PYTHONPATH="/app"

# Environment defaults (override at runtime as needed)
ENV ELASTICSEARCH_VERIFY_CERTS=false \
    PYTHONUNBUFFERED=1

# Expose the HTTP port used when running with streamable transports
EXPOSE 8000

# Default to the Elasticsearch variant; override the command to use opensearch instead
ENTRYPOINT ["elasticsearch-mcp-server"]
CMD ["--transport", "stdio"]

