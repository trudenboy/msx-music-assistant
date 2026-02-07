ARG BUILD_FROM
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    ffmpeg \
    curl \
    jq \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY bridge/ ./bridge/
COPY rootfs/ /

# Create non-root user
RUN adduser -D -u 1000 addon && \
    chown -R addon:addon /app

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8099/health || exit 1

# Expose port
EXPOSE 8099

# Run as non-root
USER addon

# Labels
LABEL \
    io.hass.name="MSX Music Assistant Bridge" \
    io.hass.description="Stream Music Assistant to Smart TVs" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}"

# Entrypoint
CMD ["/usr/bin/run.sh"]
