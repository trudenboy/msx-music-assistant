#!/usr/bin/with-contenv bashio

# Read configuration from HA
export LOG_LEVEL=$(bashio::config 'log_level')
export ENABLE_TRANSCODING=$(bashio::config 'enable_transcoding')
export OUTPUT_FORMAT=$(bashio::config 'output_format')
export OUTPUT_QUALITY=$(bashio::config 'output_quality')

# Music Assistant is usually available through internal network
export MA_HOST="${MA_HOST:-music-assistant}"
export MA_PORT="${MA_PORT:-8095}"
export MA_STREAM_PORT="${MA_STREAM_PORT:-8097}"

bashio::log.info "Starting MSX-MA Bridge..."
bashio::log.info "Music Assistant: ${MA_HOST}:${MA_PORT}"
bashio::log.info "Transcoding: ${ENABLE_TRANSCODING} (${OUTPUT_FORMAT} @ ${OUTPUT_QUALITY}kbps)"

# Start Python server
cd /app
exec python -m bridge.server
