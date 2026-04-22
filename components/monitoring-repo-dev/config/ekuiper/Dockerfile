FROM dockerhub.timeweb.cloud/lfedge/ekuiper:2.2.3-alpine-python

# Switch to root to install packages
USER root

# Настраиваем зеркало Selectel
RUN ALPINE_VERSION=$(cat /etc/alpine-release | cut -d. -f1,2) && \
    echo "https://mirror.selectel.ru/alpine/v${ALPINE_VERSION}/main" > /etc/apk/repositories && \
    echo "https://mirror.selectel.ru/alpine/v${ALPINE_VERSION}/community" >> /etc/apk/repositories

# Install required utilities for init script
RUN apk add --no-cache \
    zip \
    curl \
    bash

# Create plugin directories (for external mounting)
RUN mkdir -p /kuiper/plugins/sinks /kuiper/plugins/sources && \
    chown -R kuiper:kuiper /kuiper/plugins

# Copy custom entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy init directory
COPY init/ /kuiper/init/
RUN chmod +x /kuiper/init/init.sh && \
    chown -R kuiper:kuiper /kuiper/init

# Switch back to kuiper user
USER kuiper

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]

