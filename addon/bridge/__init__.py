"""MSX Music Assistant Bridge - Main package."""
__version__ = "1.0.0"
__author__ = "MSX-MA Contributors"

from .server import MSXBridgeServer
from .ma_client import MusicAssistantClient
from .stream_proxy import StreamProxy
from .codec_handler import CodecHandler

__all__ = [
    'MSXBridgeServer',
    'MusicAssistantClient', 
    'StreamProxy',
    'CodecHandler'
]
