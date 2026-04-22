# Multi-stage build for optimized production image
FROM registry.dmi-msk.ru/base-images:python3.13-slim-master AS builder

WORKDIR /build

# Настраиваем зеркало Selectel
RUN echo "deb http://mirror.selectel.ru/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirror.selectel.ru/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirror.selectel.ru/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better caching
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir --user --index-url=https://mirrors.ustc.edu.cn/pypi/simple/ .[dev]


# Production image
FROM registry.dmi-msk.ru/base-images:python3.13-slim-master

# ARG MODE=dev

WORKDIR /service

# Настраиваем зеркало Selectel
RUN echo "deb http://mirror.selectel.ru/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirror.selectel.ru/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirror.selectel.ru/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    mosquitto-clients \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# TODO: figure out how to install dev dependencies only for local development without using ARG
# Install dev dependencies if in dev mode
# RUN if [ "$MODE" = "dev" ]; then \
#         pip install --no-cache-dir .[dev]; \
#     fi

RUN chmod +x entrypoint.sh

EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

ENTRYPOINT ["./entrypoint.sh"]
