"""MSX Music Assistant Bridge Server."""
import asyncio
import logging
import os
from pathlib import Path

from aiohttp import web
import aiofiles

from .stream_proxy import StreamProxy
from .ma_client import MusicAssistantClient
from .codec_handler import CodecHandler

logger = logging.getLogger(__name__)


class MSXBridgeServer:
    """Main server class for MSX-MA Bridge."""

    def __init__(self, config):
        """Initialize server with configuration."""
        self.config = config
        self.app = web.Application()
        self.ma_client = MusicAssistantClient(
            host=config['ma_host'],
            port=config['ma_port']
        )
        self.stream_proxy = StreamProxy(
            ma_client=self.ma_client,
            codec_handler=CodecHandler(config)
        )

        self.setup_routes()
        self.setup_cors()

    def setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/start.json', self.handle_start_json)
        self.app.router.add_get('/msx-plugin.js', self.handle_plugin_js)
        self.app.router.add_get('/stream/{track_uri}', self.handle_stream)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/ws', self.handle_websocket)

    def setup_cors(self):
        """Setup CORS middleware."""
        @web.middleware
        async def cors_middleware(request, handler):
            if request.method == 'OPTIONS':
                return web.Response(
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS',
                        'Access-Control-Allow-Headers': '*',
                    }
                )
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        self.app.middlewares.append(cors_middleware)

    async def handle_root(self, request):
        """Serve web interface."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MSX-MA Bridge</title>
            <style>
                body {{ font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }}
                .info {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1>MSX Music Assistant Bridge</h1>
            <div class="info">
                <h3>📺 MSX Setup URL</h3>
                <code>http://{request.host}/start.json</code>
            </div>
            <div class="info">
                <h3>✅ Status</h3>
                <p>Music Assistant: Connected</p>
                <p>Active Streams: {len(self.stream_proxy.active_streams)}</p>
            </div>
            <div class="info">
                <h3>🔧 Configuration</h3>
                <p>Transcoding: {'Enabled' if self.config['enable_transcoding'] else 'Disabled'}</p>
                <p>Output: {self.config['output_format'].upper()} @ {self.config['output_quality']}kbps</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def handle_start_json(self, request):
        """Serve MSX start.json."""
        start_json = {
            "name": "Music Assistant",
            "version": "1.0.0",
            "parameter": "interaction:init",
            "scripts": [f"http://{request.host}/msx-plugin.js"]
        }
        return web.json_response(start_json)

    async def handle_plugin_js(self, request):
        """Serve compiled interaction plugin."""
        plugin_path = Path(__file__).parent.parent / 'frontend' / 'msx-plugin.js'
        async with aiofiles.open(plugin_path, 'r') as f:
            content = await f.read()
        return web.Response(text=content, content_type='application/javascript')

    async def handle_stream(self, request):
        """Proxy audio stream."""
        track_uri = request.match_info['track_uri']
        logger.info(f"Stream request: {track_uri}")
        try:
            return await self.stream_proxy.proxy_stream(track_uri, request)
        except Exception as e:
            logger.error(f"Stream error: {e}")
            return web.Response(status=500, text=str(e))

    async def handle_health(self, request):
        """Health check endpoint."""
        ma_connected = await self.ma_client.is_connected()
        return web.json_response({
            "status": "ok" if ma_connected else "degraded",
            "music_assistant": "connected" if ma_connected else "disconnected"
        })

    async def handle_websocket(self, request):
        """WebSocket relay to MA."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self.ma_client.relay_websocket(ws)
        return ws

    async def start(self):
        """Start the server."""
        await self.ma_client.connect()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8099)
        await site.start()
        logger.info("MSX-MA Bridge started on http://0.0.0.0:8099")
        await asyncio.Event().wait()


if __name__ == '__main__':
    config = {
        'ma_host': os.getenv('MA_HOST', 'music-assistant'),
        'ma_port': int(os.getenv('MA_PORT', 8095)),
        'ma_stream_port': int(os.getenv('MA_STREAM_PORT', 8097)),
        'enable_transcoding': os.getenv('ENABLE_TRANSCODING', 'true').lower() == 'true',
        'output_format': os.getenv('OUTPUT_FORMAT', 'mp3'),
        'output_quality': int(os.getenv('OUTPUT_QUALITY', 320))
    }
    logging.basicConfig(level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper()))
    server = MSXBridgeServer(config)
    asyncio.run(server.start())
