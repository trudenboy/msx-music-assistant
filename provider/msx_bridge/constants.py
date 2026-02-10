"""Constants for the MSX Bridge Provider."""

import re

CONF_HTTP_PORT = "http_port"
CONF_OUTPUT_FORMAT = "output_format"
CONF_PLAYER_IDLE_TIMEOUT = "player_idle_timeout"
CONF_SHOW_STOP_NOTIFICATION = "show_stop_notification"
CONF_ABORT_STREAM_FIRST = "abort_stream_first"
CONF_PLAYBACK_MODE = "playback_mode"

DEFAULT_HTTP_PORT = 8099
DEFAULT_OUTPUT_FORMAT = "mp3"
DEFAULT_PLAYER_IDLE_TIMEOUT = 30  # minutes
DEFAULT_SHOW_STOP_NOTIFICATION = False
DEFAULT_ABORT_STREAM_FIRST = False

# Playback modes for how MSX and MA coordinate queues/streams.
# "legacy" keeps the current behavior (flow stream for /msx/audio),
# while the named modes are used by new features:
# - "radio": single long flow stream, MSX behaves like a radio client;
# - "native_playlist": MSX-native playlist without MA queue coupling;
# - "hybrid_playlist_queue": MSX playlist UI + per-track playback via MA queue.
DEFAULT_PLAYBACK_MODE = "legacy"

# Player ID prefix for dynamically registered players
MSX_PLAYER_ID_PREFIX = "msx_"

# Sanitize device_id or IP for use in player_id (alphanumeric + underscore only)
PLAYER_ID_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_]+")
